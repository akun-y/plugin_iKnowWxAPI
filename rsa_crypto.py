# -*- coding: utf-8 -*-
# Created: 08/06/2024
# Author: Akun.yunqi

import base64
import os
from Crypto.Signature import pkcs1_15  # 用于签名/验签
from Crypto.Cipher import PKCS1_v1_5  # 用于加密
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA


class RsaCode:
    def __init__(self, public_key=None, private_key=None):
        self.public_key = public_key
        self.private_key = private_key

    def sign(self, text):
        """
        私钥签名
        """
        signer_pri_obj = pkcs1_15.new(RSA.import_key(self.private_key))
        rand_hash = SHA256.new(text.encode())
        signature = signer_pri_obj.sign(rand_hash)
        return base64.b64encode(signature).decode("utf-8")

    def verify(self, pubkey, text, sign_result):
        """
        RSA验签
        """
        try:
            signature = base64.b64decode(sign_result)
            verifier = pkcs1_15.new(RSA.import_key(pubkey))
            rand_hash = SHA256.new(text.encode())
            verifier.verify(rand_hash, signature)
            return True
        except (ValueError, TypeError):
            return False

    def long_encrypt(self, msg):
        msg = msg.encode("utf-8")
        length = len(msg)
        default_length = 245  # PKCS1_v1_5 with RSA 2048 allows 245 bytes
        pubobj = PKCS1_v1_5.new(RSA.import_key(self.public_key))
        if length <= default_length:
            return base64.b64encode(pubobj.encrypt(msg)).decode("utf-8")
        offset = 0
        res = []
        while length - offset > 0:
            if length - offset > default_length:
                res.append(pubobj.encrypt(msg[offset : offset + default_length]))
            else:
                res.append(pubobj.encrypt(msg[offset:]))
            offset += default_length
        byte_data = b"".join(res)
        return base64.b64encode(byte_data).decode("utf-8")

    def long_decrypt(self, msg):
        msg = base64.b64decode(msg)
        length = len(msg)
        default_length = 256  # RSA 2048 produces 256 bytes blocks
        priobj = PKCS1_v1_5.new(RSA.import_key(self.private_key))
        if length <= default_length:
            return priobj.decrypt(msg, None).decode("utf-8")
        offset = 0
        res = []
        while length - offset > 0:
            if length - offset > default_length:
                res.append(priobj.decrypt(msg[offset : offset + default_length], None))
            else:
                res.append(priobj.decrypt(msg[offset:], None))
            offset += default_length
        return b"".join(res).decode("utf-8")


def generate_keys(public_key_file="public_key.pem", private_key_file="private_key.pem"):
    key = RSA.generate(2048)
    private_key = key.export_key()
    public_key = key.publickey().export_key()

    with open(private_key_file, "wb") as priv_file:
        priv_file.write(private_key)

    with open(public_key_file, "wb") as pub_file:
        pub_file.write(public_key)

    return public_key, private_key


def load_pubkey_file(public_key_file="public_key.pem"):
    with open(public_key_file, "rb") as pub_file:
        public_key = pub_file.read()

    return public_key


def load_prikey_file(private_key_file="private_key.pem"):
    with open(private_key_file, "rb") as priv_file:
        private_key = priv_file.read()

    return private_key


if __name__ == "__main__":
    # 生成并写入公私钥
    generate_keys()

    # 加载公私钥
    public_key = load_pubkey_file()
    private_key = load_prikey_file()

    # 确认加载的公私钥内容
    print(f"Public Key: {public_key.decode()}")
    print(f"Private Key: {private_key.decode()}")

    # 初始化RsaCode对象
    rsa = RsaCode(public_key=public_key, private_key=private_key)

    # 测试签名和验签
    text = "python rsa test"
    print("1 开始签名")
    sign_result = rsa.sign(text)
    print("- 签名结果为: {}".format(sign_result))
    print("2 验证签名")
    verify_result = rsa.verify(public_key, text, sign_result)
    print("- 验证结果为: {}".format(verify_result))

    # 测试加密和解密
    params = '{ "username": "python rsa" }'
    print("3 开始RSA加密")
    en_result = rsa.long_encrypt(params)
    print("- 加密结果为: {}".format(en_result))
    print("4 开始RSA解密")
    de_result = rsa.long_decrypt(en_result)
    print("- 解密结果为: {}".format(de_result))
