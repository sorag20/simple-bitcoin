import Crypto
import Crypto.Random
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
# RSA の鍵ペアを生成する
def generate_rsa_key_pair():
    random_gen = Crypto.Random.new().read
    private_key = RSA.generate(2048, random_gen)
    public_key = private_key.publickey()
    return public_key, private_key

def main():
    test_txt = "This is test message for getting understand about digital signature"

    pubkey, privkey = generate_rsa_key_pair()
    #公開鍵で暗号化
    byte_txt= test_txt.encode('utf-8')
    cipher = PKCS1_OAEP.new(pubkey)
    cipher_text = cipher.encrypt(byte_txt)
    print("encrypto :", cipher_text)
    #秘密鍵で復号
    cipher_dec = PKCS1_OAEP.new(privkey)
    decrypted_text = cipher_dec.decrypt(cipher_text)
    print("decrypto:", decrypted_text)
    if test_txt == decrypted_text.decode('utf-8'):
        print("test_txt and decrypto are same!")

if __name__ == '__main__':
    main()