#include <stdint.h>

__constant__ unsigned char target[32];

__constant__ unsigned char nbits[4];
__constant__ unsigned char ntime[4];
__constant__ unsigned char version[4];
__constant__ unsigned char previous_block_hash[32];

__constant__ int len_extranonce2;
__constant__ int len_prefix_coinbase;
__constant__ int len_suffix_coinbase;
__constant__ int merkle_branch_depth;

__device__ uint32_t result_nonce;


#define ROTRIGHT(word, bits) (((word) >> (bits)) | ((word) << (32 - (bits))))
#define CH(x, y, z) (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x, y, z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define EP0(x) (ROTRIGHT(x, 2) ^ ROTRIGHT(x, 13) ^ ROTRIGHT(x, 22))
#define EP1(x) (ROTRIGHT(x, 6) ^ ROTRIGHT(x, 11) ^ ROTRIGHT(x, 25))
#define SIG0(x) (ROTRIGHT(x, 7) ^ ROTRIGHT(x, 18) ^ ((x) >> 3))
#define SIG1(x) (ROTRIGHT(x, 17) ^ ROTRIGHT(x, 19) ^ ((x) >> 10))



__constant__ unsigned int k[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
};

__device__ void sha256_transform(unsigned int *state, const unsigned char *data) {
    unsigned int a, b, c, d, e, f, g, h, t1, t2;//, m[64];
    unsigned int w[64];

    a = state[0];
    b = state[1];
    c = state[2];
    d = state[3];
    e = state[4];
    f = state[5];
    g = state[6];
    h = state[7];

    for (int i = 0; i < 16; i++) {
        w[i] = (data[i * 4] << 24) | (data[i * 4 + 1] << 16) | (data[i * 4 + 2] << 8) | data[i * 4 + 3];
    }

    for (int i = 16; i < 64; i++) {
        w[i] = SIG1(w[i - 2]) + w[i - 7] + SIG0(w[i - 15]) + w[i - 16];
    }

    for (int i = 0; i < 64; i++) {
        t1 = h + EP1(e) + CH(e, f, g) + k[i] + w[i];
        t2 = EP0(a) + MAJ(a, b, c);
        h = g;
        g = f;
        f = e;
        e = d + t1;
        d = c;
        c = b;
        b = a;
        a = t1 + t2;
    }

    state[0] += a;
    state[1] += b;
    state[2] += c;
    state[3] += d;
    state[4] += e;
    state[5] += f;
    state[6] += g;
    state[7] += h;
}

__device__ void sha256(const unsigned char *message, int length, unsigned char *output) {
    unsigned int state[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };

    int padded_length = length + 9;
    while (padded_length % 64 != 0) padded_length++;
    unsigned char padded_message[448];
    memcpy(padded_message, message, length);

    padded_message[length] = 0x80;
    for (int i = length + 1; i < padded_length - 8; i++) {
        padded_message[i] = 0;
    }

    unsigned long long bit_length = length * 8;
    for (int i = 0; i < 8; i++) {
        padded_message[padded_length - 8 + i] = (bit_length >> (56 - i * 8)) & 0xff;
    }

    for (int i = 0; i < padded_length; i += 64) {
        sha256_transform(state, padded_message + i);
    }
    for (int i = 0; i < 8; i++) {
        output[i * 4] = (state[i] >> 24) & 0xff;
        output[i * 4 + 1] = (state[i] >> 16) & 0xff;
        output[i * 4 + 2] = (state[i] >> 8) & 0xff;
        output[i * 4 + 3] = state[i] & 0xff;
    }
}

// sha256 twice
__device__ void double_sha256(const unsigned char *_input, int len, unsigned char *_output) {
    unsigned char __hash1[32];
    sha256(_input, len, __hash1);
    sha256(__hash1, 32, _output);
}

// generate random extranonce
__device__ void generate_random_extranonce(unsigned char *_output) {
    //int __tid = threadIdx.x + blockIdx.x * blockDim.x;
    unsigned int __seed;
    for(int i = 0; i < len_extranonce2; i++){
        __seed = clock64() ^ (threadIdx.x * 0x96d6) ^ (blockIdx.x * 0xf6b6);
        //_output[__tid * len_extranonce2 + i] = (uint8_t)((__seed + (blockIdx.x * blockDim.x + threadIdx.x)) % 255);
        _output[i] = (unsigned char)((__seed + (blockIdx.x * blockDim.x + threadIdx.x)) % 255);
    }
}

// generate random nonce
__device__ uint32_t generate_random_nonce()
{
    uint32_t __nonce = (clock64() ^ (threadIdx.x * 0x96d6) ^ (blockIdx.x * 0xf6b6)) & 0xFFFFFFFF;
    return __nonce;
}

// create merkle root
__device__ void build_merkle_root(unsigned char *_coinbaseId, unsigned char *_merkle_branch) {
    unsigned char __temp[32];
    memcpy(__temp, _coinbaseId, 32);

    for (int i = 0; i < merkle_branch_depth; i +=32) {
        unsigned char __combined[64];
        memcpy(__combined, __temp, 32);
        memcpy(__combined + 32, _merkle_branch + i, 32);
        double_sha256(__combined, 64, __temp);
    }
    memcpy(_coinbaseId, __temp, 32);
}

// create pre header 76 bytes
__device__ void build_pre_header(unsigned char *_merkle_root, unsigned char *_header) {
    memset(_header, 0, 80);
    memcpy(_header, version, 4);
    memcpy(_header + 4, previous_block_hash, 32);
    memcpy(_header + 36, _merkle_root, 32);
    memcpy(_header + 68, ntime, 4);
    memcpy(_header + 72, nbits, 4);
}

__device__ void reverse_bytes(unsigned char *arr, int size) {
    for (int i = 0; i < size / 2; i++) {
        unsigned char temp = arr[i];
        arr[i] = arr[size - 1 - i];
        arr[size - 1 - i] = temp;
    }
}

//check target and hash
__device__ bool check_target(unsigned char *_header_hash) {
    reverse_bytes(_header_hash, 32);
    for (int i = 0; i < 32; i++)
    {
        if (_header_hash[i] < target[i]) return true;
        if (_header_hash[i] > target[i]) return false;
    }
    return false;
}

__global__ void mine_kernel(unsigned char * _prefix_coinbase, unsigned char * _suffix_coinbase,
                            unsigned char *_merkle_branch, unsigned char *_extranonce2) {

    int __len_coinbase = len_prefix_coinbase + len_extranonce2 + len_suffix_coinbase;
    unsigned char __extranonce2_buffer[32];
    unsigned char __coinbase_buffer[200];

    unsigned char *__extranonce2 = __extranonce2_buffer;
    unsigned char *__coinbase = __coinbase_buffer;

    unsigned char __coinbaseID[32];

    unsigned char __header[80];
    unsigned char __header_hash[32];

    uint32_t __nonce;

    int __extranonce2_loop_counter = 0;
    const int __extranonce2_loop_limit = 8;

    int __nonce_counter = 0;
    //const uint32_t __nonce_limit = 77164; // for 50% chance of duplicate
    //const uint32_t __nonce_limit = 20990; // for 5% chance of duplicate
    //const uint32_t __nonce_limit = 9299; // for 1% chance of duplicate
    const int __nonce_limit = 6554; // for 0.5% chance of duplicate

    while (__extranonce2_loop_counter <= __extranonce2_loop_limit && result_nonce == 0xFFFFFFFF){
        generate_random_extranonce(__extranonce2);

        // build coinbase
        memcpy(__coinbase , _prefix_coinbase, len_prefix_coinbase);
        memcpy(__coinbase + len_prefix_coinbase, __extranonce2, len_extranonce2);
        memcpy(__coinbase + len_prefix_coinbase + len_extranonce2, _suffix_coinbase, len_suffix_coinbase);


        // create coinbase transaction ID
        double_sha256(__coinbase, __len_coinbase, __coinbaseID);

        build_merkle_root(__coinbaseID, _merkle_branch);

        build_pre_header(__coinbaseID, __header);
        __nonce_counter = 0;
        // false if one thread find nonce valid_nonce = 0xFFFFFFFF;
        while (__nonce_counter <= __nonce_limit && result_nonce == 0xFFFFFFFF){
            __nonce = generate_random_nonce();

            // add nonce to header
            __header[76] = (__nonce >> 24) & 0xFF;
            __header[77] = (__nonce >> 16) & 0xFF;
            __header[78] = (__nonce >> 8) & 0xFF;
            __header[79] = __nonce & 0xFF;
            double_sha256(__header, 80, __header_hash);
            if (check_target(__header_hash))
            {
                atomicExch(&result_nonce, __nonce);
                for (int i = 0; i < len_extranonce2; i++){
                    _extranonce2[i] = __extranonce2[i];
                }
            }
            __nonce_counter += 1;
        } // end of __nonce loop
        __extranonce2_loop_counter += 1;
    } // end og __extranonce2 loop
} // end of kernel
