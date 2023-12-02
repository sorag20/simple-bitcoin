import Crypto
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Cipher import PKCS1_OAEP

from Crypto.Hash import SHA256

import copy
import binascii
import json

class RSAUtil:

    def __init__(self):
        pass

    def verify_signature(self, message, signature, sender_public_key):
        print('verify_signature was called')
        hashed_message = SHA256.new(message.encode('utf8'))
        verifier = PKCS1_v1_5.new(sender_public_key)
        result = verifier.verify(hashed_message, binascii.unhexlify(signature))
        print(result)
        return result

    def encrypt_with_pubkey(self, target, pubkey_text):
        """
        与えられた公開鍵で暗号化する
        """
        print("🎍")
        print(target)
        print("🎍")
        print(pubkey_text)
        pubkey = RSA.importKey(binascii.unhexlify(pubkey_text))
        cipher = PKCS1_OAEP.new(pubkey)
        encrypto = cipher.encrypt(target)
        return encrypto

    def verify_sbc_transaction_sig(self, transaction):
        """
        simple_bitcoin のTransactionの署名の正当性を検証する
        """
        print('verify_sbc_transaction_sig was called')
        sender_pubkey_text, used_outputs = self._get_pubkey_from_sbc_transaction(transaction)
        signature = transaction['signature']
        c_transaction = copy.deepcopy(transaction)
        del c_transaction['signature']
        target_txt = json.dumps(c_transaction, sort_keys=True)
        sender_pubkey = RSA.importKey(binascii.unhexlify(sender_pubkey_text))
        result = self.verify_signature(target_txt, signature, sender_pubkey)
        return result, used_outputs

    def _get_pubkey_from_sbc_transaction(self, transaction):
        print('_get_pubkey_from_sbc_transaction was called')
        input_t_list = transaction['inputs']
        used_outputs = []
        sender_pubkey = ''
        for i in input_t_list:
            idx = i['output_index']
            tx = i['transaction']['outputs'][idx]
            used_outputs.append(tx)
            sender_pubkey = tx['recipient']

        return sender_pubkey, used_outputs

    def verify_general_transaction_sig(self, transaction):
        """
        simple_bitcoin 以外のTransactionも署名の形式を統一することで検証を可能にしておく
        """
        print('verify_general_transaction_sig was called')
        sender_pubkey_text = transaction['sender']
        signature = transaction['signature']
        c_transaction = copy.deepcopy(transaction)
        del c_transaction['signature']
        target_txt = json.dumps(c_transaction, sort_keys=True)
        sender_pubkey = RSA.importKey(binascii.unhexlify(sender_pubkey_text))
        result = self.verify_signature(target_txt, signature, sender_pubkey)
        return result
