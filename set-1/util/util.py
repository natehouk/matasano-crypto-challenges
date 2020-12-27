import binascii
import codecs
import base64
from util.freq import englishFreqMatchScore

# Takes a hex string return a base64 string
def hex2base64(hex):
    return codecs.encode(codecs.decode(hex, 'hex'), 'base64').decode()

# Decode hex value
def decode_hex(hex):
    return bytes.fromhex(hex).decode('latin-1')

# Encode to hex
def encode_hex(value):
    return binascii.hexlify(bytes(value, 'latin-1'))

# Decode base64 value
def decode_base64(b64):
    return str(base64.b64decode(b64), 'latin-1')

# xor two equal length strings together and return a string
def xor(a, b):
    assert len(a) == len(b)
    if len(a) > len(b):
        return "".join([chr(ord(x) ^ ord(y)) for (x, y) in zip(a[:len(b)], b)])
    else:
        return "".join([chr(ord(x) ^ ord(y)) for (x, y) in zip(a, b[:len(a)])])

# Brute force ciphers with single byte key and return list of candidate plaintexts
def brute(ciphers):
    candidates = []
    for cipher in ciphers:
        for i in range(0, 256):
            key = chr(i)
            candidates.append((key, decrypt(cipher, key)))
    return candidates

# Score list of candidate texts by English word frequency and return top 5 candidate plaintexts
def score(candidates):
    results = []
    for candidate in candidates:
        score = englishFreqMatchScore(candidate[1])
        results.append((score, candidate[0], candidate[1]))
    results = sorted(results, reverse=True)[:5]
    return results

# Decrypt cipher with repeating-key xor with given key and return plaintext
def decrypt(cipher, key):
    plaintext = ""
    count = 0
    for cipher_byte in str(cipher):
        index = count % len(key)
        key_byte = key[index]
        plaintext = plaintext + xor(cipher_byte, key_byte)
        count += 1
    return plaintext

# Encrypt plaintext with repeating-key xor with given key and return cipher
def encrypt(plaintext, key):
    cipher = ""
    count = 0
    for plaintext_byte in plaintext:
        index = count % len(key)
        key_byte = key[index]
        cipher = cipher + xor(plaintext_byte, key_byte)
        count += 1
    return encode_hex(cipher)

# Load hex strings from file
def load(filename):
    with open(filename) as file:
        lines = []
        for line in file:
            lines.append(decode_hex(line.rstrip("\n")))
    return lines

# Calculate hamming difference between two inputs the hamming difference is simply the number of differing bits
def hamming(a, b):
    assert len(a) == len(b)
    a = "".join(format(ord(x), '08b') for x in str(a))
    b = "".join(format(ord(x), '08b') for x in str(b))
    return sum(x != y for x, y in zip(a, b))

# Process file and find keysize (between 1-50) which produces smallest average hamming distance
def guess_keysize(filename):
    with open(filename) as file:
        decoded = decode_base64(file.read().replace("\n", ""))
        distances = []
        for keysize in range(1, 50):
            distance = average_distance(decoded, keysize)
            distances.append((distance, keysize))
        distances = sorted(distances)
    return distances

# Calculate the average distance between keysized blocks
def average_distance(decoded, keysize):
    totalDistance = 0.0
    chunkCount = 0
    chunk = decoded[:keysize]
    while chunk != "":
        prevChunk = chunk
        chunkCount += 1
        chunk = decoded[chunkCount*keysize:chunkCount*keysize+keysize]
        if (len(chunk) == 0):
            chunkCount -= 1
            break
        totalDistance += float(hamming(prevChunk[:len(chunk)], chunk)) / min(len(chunk), float(keysize))
    return totalDistance / chunkCount

# Brute force the file with the known keysize using repeating-key xor
def transpose(filename, keysize):
    with open(filename) as file:
        blocks = {}
        chunkCount = 0
        decoded = decode_base64(file.read().replace("\n", ""))
        chunk = decoded[:keysize]
        while chunk != "":
            for byte_index in range (0, min(len(chunk), keysize)):
                blocks[byte_index, chunkCount] = chunk[byte_index]
            chunkCount += 1
            chunk = decoded[chunkCount*keysize:chunkCount*keysize+keysize]
            if (len(chunk) == 0):
                chunkCount -= 1
                break
        key = ""
        for x in range(0, keysize):
            cipher = ""
            for y in range(0, chunkCount):
                cipher = cipher + blocks[x,y]
            ciphers = [cipher]
            result = score(brute(ciphers))
            key = key + result[0][1]
    print("Key: " + key)
    return decrypt(decoded, key)

# Compare chunks by counting repeating blocks as an indicator of ECB encryption
def detect_aes_ecb(decoded):
    keysize = 16
    totalDistance = 0.0
    matches = 0
    chunk_xCount = 0
    chunk_x = decoded[:keysize]
    while chunk_x != "":
        chunk_yCount = 0
        chunk_y = decoded[:keysize]
        while chunk_y != "":
            distance = float(hamming(chunk_x[:min(len(chunk_x), len(chunk_y))], chunk_y[:min(len(chunk_x), len(chunk_y))])) / min(len(chunk_x), len(chunk_y), float(keysize))
            if (chunk_x == chunk_y or distance == 0):
                matches += 1
            totalDistance += distance
            chunk_yCount += 1
            chunk_y = decoded[chunk_yCount*keysize:chunk_yCount*keysize+keysize]
            if (len(chunk_y) == 0):
                chunk_yCount -= 1
                break
        chunk_xCount += 1
        chunk_x = decoded[chunk_xCount*keysize:chunk_xCount*keysize+keysize]
        if (len(chunk_x) == 0):
            chunk_xCount -= 1
            break
    return (totalDistance / chunk_xCount, matches)