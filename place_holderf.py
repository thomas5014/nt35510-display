def is_palindrome(string):
    string.replace(" ","").replace("'","").lower()
    str_len = len(string)
    if str_len % 2 == 0:
        return string[]