from hashlib import sha1


def make_key(param1, param2):
    hash_key_args = ''.join((param1, param2))
    hash_obj = sha1(hash_key_args.encode())
    hash_key = hash_obj.hexdigest()
    return hash_key

