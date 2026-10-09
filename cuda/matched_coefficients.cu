// Separate bounded small-coefficient CPU/CUDA research ABI.
#include <cuda_runtime.h>
#include <cstdint>
#include <cstring>
#include <new>
#include <initializer_list>

struct Pattern { int w, a, b, c; };
struct Support { int i, j, k, a, b, c; };
static_assert(sizeof(int) == 4 && sizeof(Pattern) == 16, "fixed local coefficient ABI");
struct Session {
    int64_t* host = nullptr;
    int64_t* device = nullptr;
    Pattern* device_patterns = nullptr;
    uint8_t* mask = nullptr;
    Pattern patterns[42];
    int counts[3] = {0, 0, 0};
    int backend, n, m, q, width, domain = 0, patterns_count = 0;
};
static bool prime(int q) {
    if (q < 2 || q > 65521) return false;
    for (int d = 2; d * d <= q; ++d) if (q % d == 0) return false;
    return true;
}
__host__ __device__ static int choose(int m, int w) {
    if (w == 1) return m;
    if (w == 2) return m * (m - 1) / 2;
    return m * (m - 1) * (m - 2) / 6;
}
__host__ __device__ static Support decode(int ordinal, int m, const Pattern* patterns,
                                         int c1, int c2, int c3) {
    int counts[3] = {c1, c2, c3}, w = 1, base = 0;
    for (; w <= 3; ++w) {
        int block = choose(m, w) * counts[w-1];
        if (ordinal < block) break;
        ordinal -= block;
        base += counts[w-1];
    }
    Pattern p = patterns[base + ordinal % counts[w-1]];
    int rank = ordinal / counts[w-1], i = 0, j = 0, k = 0;
    if (w == 1) i = rank;
    if (w == 2) {
        while (rank >= m - i - 1) { rank -= m - i - 1; ++i; }
        j = i + 1 + rank;
    }
    if (w == 3) {
        while (rank >= choose(m - i - 1, 2)) { rank -= choose(m - i - 1, 2); ++i; }
        j = i + 1;
        while (rank >= m - j - 1) { rank -= m - j - 1; ++j; }
        k = j + 1 + rank;
    }
    return {i, j, k, p.a, p.b, p.c};
}
__host__ __device__ static uint8_t valid(const int64_t* matrix, int n, int m, int q, Support s) {
    for (int row = 0; row < n; ++row) {
        int64_t value = s.a * matrix[row*m+s.i];
        if (s.b) value += s.b * matrix[row*m+s.j];
        if (s.c) value += s.c * matrix[row*m+s.k];
        if (value % q) return 0;
    }
    return 1;
}
__host__ __device__ static void write_support(int32_t* out, Support s) {
    out[0] = s.i; out[1] = s.j; out[2] = s.k;
    out[3] = s.a; out[4] = s.b; out[5] = s.c;
}
__global__ static void screen(const int64_t* matrix, const Pattern* patterns, uint8_t* mask,
                              int n, int m, int q, int c1, int c2, int c3, int offset, int count) {
    int id = blockIdx.x * blockDim.x + threadIdx.x;
    if (id < count) mask[id] = valid(matrix, n, m, q, decode(offset+id, m, patterns, c1, c2, c3));
}
__global__ static void audit_kernel(const Pattern* patterns, int32_t* output, int m,
                                    int c1, int c2, int c3, int offset, int count) {
    int id = blockIdx.x * blockDim.x + threadIdx.x;
    if (id < count) write_support(output+6*id, decode(offset+id, m, patterns, c1, c2, c3));
}
extern "C" int cc_abi_version() { return 1; }
extern "C" const char* cc_error(int code) {
    if (code == -1) return "invalid local coefficient parameters";
    if (code == -2) return "host allocation failed";
    return cudaGetErrorString(static_cast<cudaError_t>(code));
}
extern "C" int cc_runtime(int* value) { return value ? cudaRuntimeGetVersion(value) : -1; }
extern "C" int cc_sync() { return cudaDeviceSynchronize(); }
extern "C" int cc_close(void* handle) {
    if (!handle) return -1;
    auto* s = static_cast<Session*>(handle);
    int first = 0;
    if (s->backend == 1) {
        for (void* pointer : {static_cast<void*>(s->mask), static_cast<void*>(s->device_patterns),
                              static_cast<void*>(s->device)}) {
            int error = cudaFree(pointer);
            if (!first) first = error;
        }
    }
    delete[] s->host;
    delete s;
    return first;
}
extern "C" int cc_open(int backend, const int64_t* matrix, size_t entries, int n, int m, int q,
                        uint64_t b2, int bound, int width, void** output) {
    if (!output) return -1;
    *output = nullptr;
    if ((backend != 0 && backend != 1) || !matrix || n < 1 || n > 64 || m < 1 || m > 16
        || !prime(q) || b2 < 1 || b2 > 12 || b2 >= static_cast<uint64_t>(q)*q
        || bound < 1 || bound > 2 || width < 1 || width > 4096
        || entries != static_cast<size_t>(n)*m) return -1;
    for (size_t id = 0; id < entries; ++id) if (matrix[id] < 0 || matrix[id] >= q) return -1;
    auto* s = new (std::nothrow) Session;
    if (!s) return -2;
    s->backend = backend; s->n = n; s->m = m; s->q = q; s->width = width;
    const int alphabet[4] = {1, -1, 2, -2};
    for (int w = 1; w <= 3 && w <= m; ++w) {
        for (int a = 1; a <= bound; ++a) {
            for (int bi = 0; bi < (w >= 2 ? 2*bound : 1); ++bi) {
                int b = w >= 2 ? alphabet[bi] : 0;
                for (int ci = 0; ci < (w == 3 ? 2*bound : 1); ++ci) {
                    int c = w == 3 ? alphabet[ci] : 0;
                    if (static_cast<uint64_t>(a*a+b*b+c*c) > b2) continue;
                    s->patterns[s->patterns_count++] = {w, a, b, c};
                    ++s->counts[w-1];
                }
            }
        }
        s->domain += choose(m, w)*s->counts[w-1];
    }
    s->host = new (std::nothrow) int64_t[entries];
    if (!s->host) { delete s; return -2; }
    std::memcpy(s->host, matrix, entries*sizeof(int64_t));
    int error = 0;
    if (backend == 1) {
        error = cudaMalloc(reinterpret_cast<void**>(&s->device), entries*sizeof(int64_t));
        if (!error) error = cudaMalloc(reinterpret_cast<void**>(&s->device_patterns), s->patterns_count*sizeof(Pattern));
        if (!error) error = cudaMalloc(reinterpret_cast<void**>(&s->mask), width);
        if (!error) error = cudaMemcpy(s->device, s->host, entries*sizeof(int64_t), cudaMemcpyHostToDevice);
        if (!error) error = cudaMemcpy(s->device_patterns, s->patterns, s->patterns_count*sizeof(Pattern), cudaMemcpyHostToDevice);
    }
    if (error) { cc_close(s); return error; }
    *output = s;
    return 0;
}
static bool range_ok(const Session* s, int offset, int count) {
    return offset >= 0 && count >= 1 && count <= s->width && offset < s->domain && count <= s->domain-offset;
}
extern "C" int cc_batch(void* handle, int offset, int count, uint8_t* output, size_t length) {
    if (!handle || !output) return -1;
    auto* s = static_cast<Session*>(handle);
    if (!range_ok(s, offset, count) || length != static_cast<size_t>(count)) return -1;
    if (s->backend == 0) {
        for (int id = 0; id < count; ++id)
            output[id] = valid(s->host, s->n, s->m, s->q,
                               decode(offset+id, s->m, s->patterns, s->counts[0], s->counts[1], s->counts[2]));
        return 0;
    }
    screen<<<(count+127)/128, 128>>>(s->device, s->device_patterns, s->mask, s->n, s->m, s->q,
                                    s->counts[0], s->counts[1], s->counts[2], offset, count);
    int error = cudaGetLastError();
    if (!error) error = cudaMemcpy(output, s->mask, length, cudaMemcpyDeviceToHost);
    return error;
}
extern "C" int cc_audit(void* handle, int offset, int count, int32_t* output, size_t entries) {
    if (!handle || !output) return -1;
    auto* s = static_cast<Session*>(handle);
    if (!range_ok(s, offset, count) || entries != 6*static_cast<size_t>(count)) return -1;
    if (s->backend == 0) {
        for (int id = 0; id < count; ++id)
            write_support(output+6*id, decode(offset+id, s->m, s->patterns, s->counts[0], s->counts[1], s->counts[2]));
        return 0;
    }
    int32_t* device = nullptr;
    int error = cudaMalloc(reinterpret_cast<void**>(&device), entries*sizeof(int32_t));
    if (!error) {
        audit_kernel<<<(count+127)/128, 128>>>(s->device_patterns, device, s->m,
                                            s->counts[0], s->counts[1], s->counts[2], offset, count);
        error = cudaGetLastError();
        if (!error) error = cudaMemcpy(output, device, entries*sizeof(int32_t), cudaMemcpyDeviceToHost);
    }
    int cleanup = cudaFree(device);
    return error ? error : cleanup;
}
