import sys
import os

# define tokens used for lexical analysis
class token:
    def __init__(self):
        self.next = None
        self.prev = None


# subclasses of token
class operator(token):
    def __init__(self):
	token.__init__(self)
        self.value = None

class identifier(token):
    def __init__(self):
        token.__init__(self)
        self.value = None

class constant(token):
    def __init__(self):
        token.__init__(self)
        self.type = None
        self.value = None

class keyword(token):
    def __init__(self):
        token.__init__(self)
        self.value = None

class symbol(token):
    def __init__(self):
        token.__init__(self)
        self.value = None

# other token type is just for debugging purpose
# is not supposed to exist in real life compiler
class other(token):
    def __init__(self):
        token.__init__(self)
        self.value = None



def is_keyword(string):
        if string in ["if","else","while","not","RET","cvt_table","storage_area","GS"]:
            return True
        return False

def is_symbol(string):
        if string in ["{","}","(",")","[","]"]:
            return True
        return False
    




def get_token(string):
    t = None
    if string.startswith("$"):
        t = identifier()
        t.value = string[1:]

    elif string in [":=","GT","EQ","+","-"]:
        t = operator()
	t.value = {
            ":=" : "ASSIGNMENT",
            "GT" : "GT",
            "EQ" : "EQ",
            "+" : "ADD",
            "-" : "SUB"
        }.get(string)


    elif string.replace('.',',',1).isdigit():
        t = constant()
        if string.count('.') == 1:
            t.type = "FLOAT"
            t.value = float(string)
        elif string.count('.') == 0:
            t.type = "INT"
            t.value = int(string)

    elif is_keyword(string):
        t = keyword()
        t.value = {
                "if" : "IF",
                "else" : "ELSE",
                "while" : "WHILE",
                "not" : "NOT",
                "RET" : "RET",
                "cvt_table" : "CVT_TABLE",
                "storage_area" : "STORAGE_AREA",
                "GS" : "GS",
        }.get(string)

    elif is_symbol(string):
        t = symbol()
        t.value = string

    else:
        t = other()
        t.value = string

    return t







