// Local research FFI, ABI v1. Valid spans/exclusive handles are caller duties.
#include <cuda_runtime.h>
#include <cstddef>
#include <cstdint>
#include <new>

struct Session {
    int64_t* matrix = nullptr;
    uint8_t* mask = nullptr;
    int n, m, q, domain, width;
};

static bool prime(int q) {
    if (q < 2 || q > 65521) return false;
    for (int d = 2; d * d <= q; ++d) if (q % d == 0) return false;
    return true;
}

__device__ void support(int ordinal, int m, int& first, int& second, int& sign) {
    if (ordinal < m) { first = second = ordinal; sign = 0; return; }
    int rank = (ordinal - m) / 2;
    first = 0;
    while (rank >= m - first - 1) { rank -= m - first - 1; ++first; }
    second = first + 1 + rank;
    sign = 1 - 2 * ((ordinal - m) % 2);
}

__global__ void screen(const int64_t* matrix, uint8_t* mask, int n, int m, int q, int offset, int count) {
    int id = blockIdx.x * blockDim.x + threadIdx.x;
    if (id >= count) return;
    int first, second, sign;
    support(offset + id, m, first, second, sign);
    uint8_t valid = 1;
    for (int row = 0; row < n; ++row) {
        if ((matrix[row * m + first] + sign * matrix[row * m + second]) % q != 0) {
            valid = 0; break;
        }
    }
    mask[id] = valid;
}

__global__ void audit(int32_t* triples, int m, int offset, int count) {
    int id = blockIdx.x * blockDim.x + threadIdx.x;
    if (id >= count) return;
    int first, second, sign;
    support(offset + id, m, first, second, sign);
    triples[3 * id] = first; triples[3 * id + 1] = second; triples[3 * id + 2] = sign;
}

extern "C" int mg_abi_version() { return 1; }
extern "C" const char* mg_error(int code) {
    if (code == -1) return "invalid local FFI parameters";
    if (code == -2) return "host allocation failed";
    return cudaGetErrorString(static_cast<cudaError_t>(code));
}
extern "C" int mg_runtime_version(int* value) {
    if (!value) return -1;
    return cudaRuntimeGetVersion(value);
}
extern "C" int mg_close(void* handle) {
    if (!handle) return -1;
    auto* s = static_cast<Session*>(handle);
    int first = cudaFree(s->mask);
    int second = cudaFree(s->matrix);
    delete s;
    return first ? first : second;
}
extern "C" int mg_open(const int64_t* matrix, size_t entries, int n, int m, int q,
                        int norm_one, int width, void** output) {
    if (!output) return -1;
    *output = nullptr;
    if (!matrix || n < 1 || n > 64 || m < 1 || m > 128 || !prime(q)
        || (norm_one != 0 && norm_one != 1) || width < 1 || width > 4096
        || entries != static_cast<size_t>(n) * static_cast<size_t>(m)) return -1;
    for (size_t i = 0; i < entries; ++i) if (matrix[i] < 0 || matrix[i] >= q) return -1;
    auto* s = new (std::nothrow) Session;
    if (!s) return -2;
    s->n = n; s->m = m; s->q = q; s->width = width; s->domain = norm_one ? m : m * m;
    int error = cudaMalloc(reinterpret_cast<void**>(&s->matrix), entries * sizeof(int64_t));
    if (!error) error = cudaMalloc(reinterpret_cast<void**>(&s->mask), static_cast<size_t>(width));
    if (!error) error = cudaMemcpy(s->matrix, matrix, entries * sizeof(int64_t), cudaMemcpyHostToDevice);
    if (error) { mg_close(s); return error; }
    *output = s;
    return 0;
}
static bool valid_range(const Session* s, int offset, int count) {
    return offset >= 0 && count >= 1 && count <= s->width && offset < s->domain
        && count <= s->domain - offset;
}
extern "C" int mg_batch(void* handle, int offset, int count, uint8_t* mask, size_t length) {
    if (!handle || !mask) return -1;
    auto* s = static_cast<Session*>(handle);
    if (!valid_range(s, offset, count) || length != static_cast<size_t>(count)) return -1;
    screen<<<(count + 127) / 128, 128>>>(s->matrix, s->mask, s->n, s->m, s->q, offset, count);
    int error = cudaGetLastError();
    if (!error) error = cudaMemcpy(mask, s->mask, length, cudaMemcpyDeviceToHost);
    // Synchronous readback checks completion and async kernel errors.
    return error;
}
extern "C" int mg_audit(void* handle, int offset, int count, int32_t* triples, size_t entries) {
    if (!handle || !triples) return -1;
    auto* s = static_cast<Session*>(handle);
    if (!valid_range(s, offset, count) || entries != 3 * static_cast<size_t>(count)) return -1;
    int32_t* device = nullptr;
    int error = cudaMalloc(reinterpret_cast<void**>(&device), entries * sizeof(int32_t));
    if (!error) {
        audit<<<(count + 127) / 128, 128>>>(device, s->m, offset, count);
        error = cudaGetLastError();
        if (!error) error = cudaMemcpy(triples, device, entries * sizeof(int32_t), cudaMemcpyDeviceToHost);
    }
    int cleanup = cudaFree(device);
    return error ? error : cleanup;
}
