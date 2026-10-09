// Spec/20 local trusted FFI; CPU cursor and independently dispatched GPU decode.
#include <cuda_runtime.h>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <new>

struct Support { int i, j, k, b, c; };
struct Session {
    int64_t* host = nullptr;
    int64_t* device = nullptr;
    uint8_t* mask = nullptr;
    int backend, n, m, q, weight, width, domain;
};
static bool prime(int q) {
    if (q < 2 || q > 65521) return false;
    for (int d = 2; d * d <= q; ++d) if (q % d == 0) return false;
    return true;
}
__host__ __device__ static int choose2(int n) { return n * (n - 1) / 2; }
__host__ __device__ static Support decode(int ordinal, int m) {
    if (ordinal < m) return {ordinal, ordinal, ordinal, 0, 0};
    if (ordinal < m * m) {
        int rank = (ordinal - m) / 2, i = 0;
        while (rank >= m - i - 1) { rank -= m - i - 1; ++i; }
        int j = i + 1 + rank;
        return {i, j, j, 1 - 2 * ((ordinal - m) % 2), 0};
    }
    int rank = (ordinal - m * m) / 4, signs = (ordinal - m * m) % 4, i = 0;
    while (rank >= choose2(m - i - 1)) { rank -= choose2(m - i - 1); ++i; }
    int j = i + 1;
    while (rank >= m - j - 1) { rank -= m - j - 1; ++j; }
    return {i, j, j + 1 + rank, 1 - 2 * (signs / 2), 1 - 2 * (signs % 2)};
}
// CPU advances nested loops/signs in O(1); only chunk starts need unranking.
static void advance(Support& s, int m) {
    if (!s.b) {
        if (++s.i < m) { s.j = s.k = s.i; return; }
        s = {0, 1, 1, 1, 0}; return;
    }
    if (!s.c) {
        if (s.b == 1) { s.b = -1; return; }
        s.b = 1;
        if (++s.j < m) { s.k = s.j; return; }
        if (++s.i < m - 1) { s.j = s.k = s.i + 1; return; }
        s = {0, 1, 2, 1, 1}; return;
    }
    if (s.c == 1) { s.c = -1; return; }
    s.c = 1;
    if (s.b == 1) { s.b = -1; return; }
    s.b = 1;
    if (++s.k < m) return;
    if (++s.j < m - 1) { s.k = s.j + 1; return; }
    ++s.i; s.j = s.i + 1; s.k = s.j + 1;
}
__host__ __device__ static uint8_t valid(const int64_t* matrix, int n, int m, int q, Support s) {
    for (int row = 0; row < n; ++row) {
        int64_t value = matrix[row * m + s.i];
        if (s.b) value += s.b * matrix[row * m + s.j];
        if (s.c) value += s.c * matrix[row * m + s.k];
        if (value % q != 0) return 0;
    }
    return 1;
}
__global__ static void screen(const int64_t* matrix, uint8_t* mask, int n, int m, int q, int offset, int count) {
    int id = blockIdx.x * blockDim.x + threadIdx.x;
    if (id < count) mask[id] = valid(matrix, n, m, q, decode(offset + id, m));
}
__host__ __device__ static void write_support(int32_t* out, Support s) {
    out[0] = s.i; out[1] = s.j; out[2] = s.k; out[3] = 1; out[4] = s.b; out[5] = s.c;
}
__global__ static void audit_kernel(int32_t* output, int m, int offset, int count) {
    int id = blockIdx.x * blockDim.x + threadIdx.x;
    if (id < count) write_support(output + 6 * id, decode(offset + id, m));
}
extern "C" int sp_abi_version() { return 1; }
extern "C" const char* sp_error(int code) {
    if (code == -1) return "invalid local FFI parameters";
    if (code == -2) return "host allocation failed";
    return cudaGetErrorString(static_cast<cudaError_t>(code));
}
extern "C" int sp_runtime(int* value) { return value ? cudaRuntimeGetVersion(value) : -1; }
extern "C" int sp_sync() { return cudaDeviceSynchronize(); }
extern "C" int sp_close(void* handle) {
    if (!handle) return -1;
    auto* s = static_cast<Session*>(handle);
    int first = 0, second = 0;
    if (s->backend == 1) { first = cudaFree(s->mask); second = cudaFree(s->device); }
    delete[] s->host;
    delete s;
    return first ? first : second;
}
extern "C" int sp_open(int backend, const int64_t* matrix, size_t entries, int n, int m, int q,
                        uint64_t b2, int max_weight, int width, void** output) {
    if (!output) return -1;
    *output = nullptr;
    if ((backend != 0 && backend != 1) || !matrix || n < 1 || n > 64 || m < 1 || m > 128
        || !prime(q) || b2 < 1 || b2 >= static_cast<uint64_t>(q) * static_cast<uint64_t>(q)
        || (max_weight != 2 && max_weight != 3) || width < 1 || width > 4096
        || entries != static_cast<size_t>(n) * static_cast<size_t>(m)) return -1;
    for (size_t i = 0; i < entries; ++i) if (matrix[i] < 0 || matrix[i] >= q) return -1;
    auto* s = new (std::nothrow) Session;
    if (!s) return -2;
    s->backend = backend; s->n = n; s->m = m; s->q = q; s->width = width;
    s->weight = b2 < static_cast<uint64_t>(max_weight) ? static_cast<int>(b2) : max_weight;
    s->domain = s->weight == 1 ? m : m * m;
    if (s->weight == 3) s->domain += 2 * m * (m - 1) * (m - 2) / 3;
    s->host = new (std::nothrow) int64_t[entries];
    if (!s->host) { delete s; return -2; }
    std::memcpy(s->host, matrix, entries * sizeof(int64_t));
    int error = 0;
    if (backend == 1) {
        error = cudaMalloc(reinterpret_cast<void**>(&s->device), entries * sizeof(int64_t));
        if (!error) error = cudaMalloc(reinterpret_cast<void**>(&s->mask), static_cast<size_t>(width));
        if (!error) error = cudaMemcpy(s->device, s->host, entries * sizeof(int64_t), cudaMemcpyHostToDevice);
    }
    if (error) { sp_close(s); return error; }
    *output = s;
    return 0;
}
static bool range_ok(const Session* s, int offset, int count) {
    return offset >= 0 && count >= 1 && count <= s->width && offset < s->domain && count <= s->domain - offset;
}
extern "C" int sp_batch(void* handle, int offset, int count, uint8_t* output, size_t length) {
    if (!handle || !output) return -1;
    auto* s = static_cast<Session*>(handle);
    if (!range_ok(s, offset, count) || length != static_cast<size_t>(count)) return -1;
    if (s->backend == 0) {
        Support support = decode(offset, s->m);
        for (int id = 0; id < count; ++id) {
            output[id] = valid(s->host, s->n, s->m, s->q, support);
            if (id + 1 < count) advance(support, s->m);
        }
        return 0;
    }
    screen<<<(count + 127) / 128, 128>>>(s->device, s->mask, s->n, s->m, s->q, offset, count);
    int error = cudaGetLastError();
    if (!error) error = cudaMemcpy(output, s->mask, length, cudaMemcpyDeviceToHost);
    return error;
}
extern "C" int sp_audit(void* handle, int offset, int count, int32_t* output, size_t entries) {
    if (!handle || !output) return -1;
    auto* s = static_cast<Session*>(handle);
    if (!range_ok(s, offset, count) || entries != 6 * static_cast<size_t>(count)) return -1;
    if (s->backend == 0) {
        Support support = decode(offset, s->m);
        for (int id = 0; id < count; ++id) {
            write_support(output + 6 * id, support);
            if (id + 1 < count) advance(support, s->m);
        }
        return 0;
    }
    int32_t* device = nullptr;
    int error = cudaMalloc(reinterpret_cast<void**>(&device), entries * sizeof(int32_t));
    if (!error) {
        audit_kernel<<<(count + 127) / 128, 128>>>(device, s->m, offset, count);
        error = cudaGetLastError();
        if (!error) error = cudaMemcpy(output, device, entries * sizeof(int32_t), cudaMemcpyDeviceToHost);
    }
    int cleanup = cudaFree(device);
    return error ? error : cleanup;
}
