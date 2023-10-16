# -*- coding: utf-8 -*-
# Created: 03/03/2021
# Author: Honest1y

import base64
import Crypto.Signature.PKCS1_v1_5 as sign_PKCS1_v1_5 #用于签名/验签
from Crypto.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5 #用于加密
from Crypto import Hash
from Crypto.PublicKey import RSA


class RsaCode(object):
    def __init__(self):
        super().__init__()
        self.public_key = "-----BEGIN PUBLIC KEY-----\nMIGJAoGBANx8VU1LpdNyKbRdGp4lnucpHOyy6g9qtWm6OSmptUiTWy4wVWoHmhh/\nGEqjcuk+jNZdA4wjFBQYq/RRyFYtoZZg68CTWDR/TDPJWoyO+qcIBBy0BLBlZc20\nJT/fflog+dPMDA9LT565IwrXFjY9qK/AZcFnxW79LlrVq05WtSVzAgMBAAE=\n-----END PUBLIC KEY-----"
        
        self.private_key = "-----BEGIN PRIVATE KEY-----\nMIICWwIBAAKBgQDcfFVNS6XTcim0XRqeJZ7nKRzssuoParVpujkpqbVIk1suMFVq\nB5oYfxhKo3LpPozWXQOMIxQUGKv0UchWLaGWYOvAk1g0f0wzyVqMjvqnCAQctASw\nZWXNtCU/335aIPnTzAwPS0+euSMK1xY2PaivwGXBZ8Vu/S5a1atOVrUlcwIDAQAB\nAoGAUgBT4Vl/JPLSm+f8nFC1lpdt0IKCFpXDPr0pwVsCtylGwhjry3FkWDP8ntXH\nSQQgcSFKznXFY+wBF+7KqXJzI7/Dar2+jrpTFrZjAWjTrQsDrM6j3DORtnoOJEWn\nNCDSkGoAEBFLAHJPOFIO+IGoe5BSfEtK/HlWWc2ajB0BxnECQQD0C3mu+h5cDII6\npmeMo0ImvG/McoWkWLPdP6IvTTAljkUTfkZMbjGDKDHhGU/T08hJ359Q8nwwzX4Z\neJBpViotAkEA50loFyAXxFMc/NHu5kQXRtC9ykK2qPVM+G/fu7V2Ro0iEm73+McR\nG1kIIH2OSWNVO1l9LGecOrFzQ7mlNTZyHwJAD43frpBQeQtvDW/nr6YEJFXkRkKS\nU/w3UoWov50K0Yn0yx5EOsDXNQXN0Av984FPBa5UCCO8WJvwSo1NnvkX7QJAK/HC\nmUI7wc2Y4GBy58VgNtBKfzeVxRx2d22qMNwVkOoX4zC6ZMZN9chAxwuUEVWSSCiE\no/87q9szb1bCkQ27OQJAY8KwILiP+Vkf+BfiNEY0dn4ec19FAfv8QJT4NS4edMsG\nOwSl6yBu40qTa6DrRCAOxohDQAl4C1yoXPrLMyxQDw==\n-----END RSA PRIVATE KEY-----\n-----END PRIVATE KEY-----"
    
    def sign(self, text):
        """
        私钥签名
        :return:
        """
        signer_pri_obj = sign_PKCS1_v1_5.new(RSA.importKey(self.private_key))
        rand_hash = Hash.SHA256.new()
        rand_hash.update(text.encode())
        signature = signer_pri_obj.sign(rand_hash)
        return base64.b64encode(signature).decode(encoding="utf-8")

    def verify(self,pubkey, text, sign_result):
        """
        RSA验签
        :param signature: 签名
        :return:
        """
        try :
            signature = base64.b64decode(sign_result)
            verifier = sign_PKCS1_v1_5.new(RSA.importKey(pubkey))
            _rand_hash = Hash.SHA256.new()
            _rand_hash.update(text.encode())
            return verifier.verify(_rand_hash, signature)
        except Exception as e:
            return False


    def long_encrypt(self, msg):
        msg = msg.encode('utf-8')
        length = len(msg)
        default_length = 64
        pubobj = Cipher_pkcs1_v1_5.new(RSA.importKey(self.public_key))
        if length < default_length:
            return base64.b64encode(pubobj.encrypt(msg)).decode(encoding="utf-8")
        offset = 0
        res = []
        while length - offset > 0:
            if length - offset > default_length:
                res.append(pubobj.encrypt(msg[offset:offset + default_length]))
            else:
                res.append(pubobj.encrypt(msg[offset:]))
            offset += default_length
        byte_data = b''.join(res)
        return base64.b64encode(byte_data).decode(encoding="utf-8")

    def long_decrypt(self, msg):
        msg = base64.b64decode(msg)
        length = len(msg)
        default_length = 75
        priobj = Cipher_pkcs1_v1_5.new(RSA.importKey(self.private_key))
        if length <= default_length:
            return priobj.decrypt(msg, b'RSA').decode(encoding="utf-8")
        offset = 0
        res = []
        while length - offset > 0:
            if length - offset > default_length:
                res.append(priobj.decrypt(msg[offset:offset + default_length], b'RSA'))
            else:
                res.append(priobj.decrypt(msg[offset:], b'RSA'))
            offset += default_length
        print()
        return b''.join(res).decode('utf-8')


if __name__ == '__main__':
    text = "python rsa test"
    print("1 开始签名")
    sign_result = RsaCode().sign(text)
    print("- 签名结果为: {}".format(sign_result))
    print("2 验证签名")
    verify_result = RsaCode().verify(text, sign_result)
    print("- 验证结果为: {}".format(verify_result))

    params = '{ "username": "python rsa" }'
    print("3 开始RSA加密")
    en_result = RsaCode().long_encrypt(params)
    print("- 加密结果为: {}".format(en_result))
    print("4 开始RSA解密")
    de_result = RsaCode().long_decrypt(en_result)
    print("- 解密结果为: {}".format(de_result))
