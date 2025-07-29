from types import NoneType
import warnings
from PIL import Image
from ast import literal_eval
from typing import Union
VALID_FUNC_CHARS = tuple("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_.0123456789")
def backslash_handler(text, end_char):
    b = False
    out = ''
    for idx, i in enumerate(text):
        if (i == end_char) and not b:
            return out, idx
        if i == '\\':
            if b:
                out += i
            b = not b
        else:
            if b:
                try:i = eval(f"\\{i}")
                except:pass
            out += i
            b = False

def find_loc(code, index, char):
    late = code[index+1:]
    if not (char in late):
        return False
    find_loop = char in "()"
    ifs = 0
    loops = 0
    i = 0
    is_if = []
    while i < len(late):
        char2 = late[i]
        if char2 == char:
            if find_loop and loops == 0:
                return index+1 + i
            if not find_loop and ifs == 0:
                return index+1 + i
        if char2 == "[":
            ifs += 1
            is_if.append(True)
        elif char2 == "]":
            if (not is_if.pop()) or ifs == 0:
                return False
            ifs -= 1
        elif char2 == "(":
            loops += 1
            is_if.append(False)
        elif char2 == ")":
            if is_if.pop() or loops == 0:
                return False
            loops -= 1
        i += 1
    return False

def convert_3rd_if(code):
    index = 0
    printer = False
    comment = False
    escaped = False
    while index < len(code):
        char = code[index]
        if char == "{":
            printer = True
        if char == "\\":
            escaped = not escaped
        if char == "}" and not escaped:
            printer = False
        if char == "/":
            comment = not comment
        stopper = printer or comment
        if char == "[" and not stopper:
            end = find_loc(code,index,"]")
            if end:
                comma = find_loc(code[:end],index,",")
                if comma:
                    next_comma = find_loc(code[:end],comma,",")
                    if next_comma:
                        previous_part = code[:index]
                        if_part = convert_3rd_if(code[index+1:comma])
                        else_part = convert_3rd_if(code[comma+1:next_comma])
                        start_part = convert_3rd_if(code[next_comma+1:end])
                        next_part = code[end+1:]
                        if_collected = "["+start_part+if_part+","+start_part+else_part+"]"
                        code = previous_part + if_collected + next_part
                        index += len(if_collected)
        index += 1
    return code

def lexer(code, optimize_=True):
    #code = convert_3rd_if(code)
    tokens = []
    print_statement = False
    comment = False
    index = 0
    if_depth = 0
    loop_depth = 0
    last_was_if = []
    prev = None
    func_name = None
    stack_number = None
    while index < len(code):
        char = code[index]
        if (not print_statement) and char == "/":
            comment = not comment
        elif (not comment) and char == "{":
            end = backslash_handler(code[index+1:],"}")
            if end is None:
                raise SyntaxError("Print statement is not terminated")
            token, new_index = end
            index += new_index + 1
            if loop_depth == 0 and if_depth == 0:
                tokens.append(("PRINT",token))
        elif not (comment or print_statement):
            if if_depth == 0 and loop_depth == 0:
                if char in VALID_FUNC_CHARS:
                    if not func_name:
                        func_name = ""
                    func_name += char
                elif func_name:
                    is_stack_number = False
                    if func_name[0].isdigit():
                        is_stack_number = all(i in "0123456789" for i in func_name)
                        if not is_stack_number:
                            raise SyntaxError("Function name cannot start with underline, dot, or a digit")
                        else:
                            stack_number = func_name
                    if func_name not in ("_",".") and not is_stack_number:
                        token = ("FUNC_NAME",func_name)
                        tokens.append(token)
                    func_name = None
            if char == "[":
                if prev != ":":
                    if_depth += 1
                    last_was_if.append(True)
                    if if_depth == 1 and loop_depth == 0:
                        if_start = index
                        else_start = None
                        special_start = None
                elif if_depth == 0 and loop_depth == 0:
                    def_start = index+1
                    index = find_loc(code,index,"]")
                    if not index:
                        raise SyntaxError("Function definition didn't finish")
                    token = ("DEF",lexer(code[def_start:index],False))
                    tokens.append(token)
            elif char == "," and if_depth == 1 and loop_depth == 0:
                if not else_start:
                    else_start = index
                    special_start = None
                else:
                    special_start = index
            elif char == "]":
                if if_depth == 0:
                    raise SyntaxError("if ended outside its statement")
                if not last_was_if.pop():
                    raise SyntaxError("If ended inside a loop")
                if_depth -= 1
                if loop_depth == 0 and if_depth == 0:
                    if special_start:
                        if_segment = code[if_start+1:else_start]
                        else_segment = code[else_start+1:special_start]
                        special_segment = code[special_start+1:index]
                        token = ("IF_ELSE_SPECIAL", lexer(if_segment,False), lexer(else_segment,False), lexer(special_segment,False))
                    elif else_start is None:
                        if_segment = code[if_start+1:index]
                        token = ("IF", lexer(if_segment,False))
                    elif else_start != (if_start +1):
                        if_segment = code[if_start+1:else_start]
                        else_segment = code[else_start+1:index]
                        token = ("IF_ELSE", lexer(if_segment,False), lexer(else_segment,False))
                    else:
                        else_segment = code[else_start+1:index]
                        token = ("ELSE",lexer(else_segment,False))
                    tokens.append(token)
                    if_segment = None
                    else_segment = None
            elif char == "(":
                if prev != ":":
                    loop_depth += 1
                    last_was_if.append(False)
                    if if_depth == 0 and loop_depth == 1:
                        loop_start = index
                elif if_depth == 0 and loop_depth == 0:
                    def_start = index+1
                    index = find_loc(code,index,")")
                    if not index:
                        raise SyntaxError("function definition didn't finish")
                    token = ("DEF_EXEC",lexer(code[def_start:index],False))
                    tokens.append(token)
            elif char == ")":
                if loop_depth == 0:
                    raise SyntaxError("loop ended outside its statement")
                if last_was_if.pop():
                    raise SyntaxError("loop ended inside an if statement")
                loop_depth -= 1
                if if_depth == 0 and loop_depth == 0:
                    loop_segment = code[loop_start+1:index]
                    token = ("LOOP",lexer(loop_segment,False))
                    tokens.append(token)
            if if_depth == 0 and loop_depth == 0 and not func_name:
                if char in "0123456789":
                    if not stack_number:
                        stack_number = ""
                    stack_number += char
                elif stack_number:
                    tokens.append(("STACK",int(stack_number)))
                    stack_number = None
                if char == ">":
                    tokens.append(("INPUT",))
                elif char == "<":
                    tokens.append(("OUTPUT",))
                elif char == "+":
                    tokens.append(("PUSH",))
                elif char == "-":
                    tokens.append(("POP",))
                elif char == "*":
                    tokens.append(("FLIP",))
                elif char == "~":
                    tokens.append(("POPPUSH",))
                elif char == "_":
                    tokens.append(("PSTACK",))
                elif char == ".":
                    tokens.append(("BREAK",))
                elif char == "^":
                    tokens.append(("PIXEL",))
                elif char == "\\":
                    tokens.append(("LINE",))
                elif char == ";":
                    tokens.append(("FRAME",))
                elif char == ",":
                    raise SyntaxError("Comma outside if or else statement")
        prev = char
        index += 1
    if comment or print_statement:
        raise SyntaxError("Comment or Print statement is not terminated")
    if if_depth != 0 or loop_depth != 0:
        raise SyntaxError("If or Loop statement is not terminated")
    if func_name:
        is_stack_number = False
        if func_name[0].isdigit() and func_name not in ("_","."):
            is_stack_number = all(i in "0123456789" for i in func_name)
            if not is_stack_number:
                raise SyntaxError("Function name cannot start with underline, dot, or a digit")
        if not is_stack_number:
            token = ("FUNC_NAME",func_name)
            tokens.append(token)
    if stack_number:
        tokens.append(("STACK",int(stack_number)))
    if optimize_:
        return optimize(tokens,rearrange=False)
    return tokens

def is_dependent(token):
    return token[0] not in ('STACK','FRAME','LINE','PRINT','POP','POPPUSH','INPUT','PSTACK','DEF')
def is_modifier(token):
    return token[0] not in ('STACK','FRAME','LINE','PRINT','PUSH','OUTPUT','PSTACK','DEF')

def optimize(tokens: list[tuple], amount=2, rearrange=True, _current_bit: int=-1) -> Union[list[tuple], tuple[list[tuple], int]]:
    if amount < 1:
        return tokens
    if rearrange:
        code = decompile(tokens)
        tokens = lexer(code)
        return tokens
    original_current_bit = _current_bit
    if _current_bit == -1:
        _current_bit = 2
    output = []
    index = 0
    length = len(tokens)
    def get_next_token(index, tokens=tokens):
        if index + 1 < len(tokens):
            return tokens[index + 1]
        return ("NOP",[], [])
    def get_next_dependent_token(index, tokens=tokens):
        next_token = get_next_token(index)
        while not is_dependent(next_token):
            index += 1
            next_token = get_next_token(index)
        return next_token
    def get_next_modifier_token(index, tokens=tokens):
        next_token = get_next_token(index)
        while not is_modifier(next_token):
            index += 1
            next_token = get_next_token(index)
        return next_token
    def is_loop(block):
        return all((sub_token[0] == 'LOOP' for sub_token in block))
    current_stack = 0
    while index < length:
        token = tokens[index]
        if token[0] in ('POP', 'INPUT'):
            _current_bit = 2
        elif token[0] == 'FLIP':
            next_token = get_next_token(index)
            if next_token[0] == 'FLIP':
                index += 2
                continue
            next_token = get_next_modifier_token(index)
            if not is_dependent(next_token):
                index += 1
                continue
            if _current_bit < 2:
                _current_bit = 1 - _current_bit
        elif token[0] == 'LOOP':
            loop_block = token[1]
            if len(loop_block) == 0 or _current_bit == 0:
                index += 1
                continue
            loop_block, temp = optimize(loop_block, amount, rearrange, _current_bit=1)
            sub_token = get_next_modifier_token(-1, loop_block)
            _current_bit = 0
            if (sub_token[0] == 'LOOP') and (temp == 0):
                output.extend(loop_block)
                index += 1
                continue
            # if temp == 1:
            #     raise RuntimeError("Loop never breaks")
            #     pass
            token = (token[0], loop_block)
        elif token[0] == 'IF':
            if_block = token[1]
            if len(if_block) == 0 or _current_bit == 0:
                index += 1
                continue
            if_block, temp = optimize(if_block, amount, rearrange, _current_bit=1)
            if is_loop(if_block):
                _current_bit = 1
            if _current_bit == 1:
                output.extend(if_block)
                _current_bit = temp
                index += 1
                continue
            token = ('IF', if_block)
        elif token[0] == 'ELSE':
            else_block = token[1]
            if len(else_block) == 0 or _current_bit == 1:
                index += 1
                continue
            else_block, temp = optimize(else_block, amount, rearrange, _current_bit=0)
            if _current_bit == 0:
                output.extend(else_block)
                _current_bit = temp
                index += 1
                continue
            _current_bit = temp
            token = ('ELSE', else_block)
        elif token[0] in ('IF_ELSE', 'IF_ELSE_SPECIAL'):
            if_block, if_temp = optimize(token[1], amount, rearrange, _current_bit=1)
            else_block, else_temp = optimize(token[2], amount, rearrange, _current_bit=0)
            if len(if_block) == 0:
                if len(else_block) == 0 or token[0] == 'IF_ELSE_SPECIAL':
                    if token[0] == 'IF_ELSE_SPECIAL':
                        if len(else_block) == 0:
                            temp, _current_bit = optimize(token[3], amount, rearrange, _current_bit=_current_bit)
                            output.extend(temp)
                        else:
                            temp_b, temp_c = optimize(token[3], amount, rearrange, _current_bit=_current_bit)
                            if _current_bit in (0, 2):
                                temp_a, temp_d = optimize(token[2], amount, rearrange, _current_bit=temp_c)
                            if _current_bit == 0:
                                output.extend(temp_b)
                                output.extend(temp_a)
                                _current_bit = temp_d
                            elif _current_bit == 1:
                                output.extend(temp_b)
                                _current_bit = temp_c
                            else:
                                output.append((token[0],[],temp_a,temp_b))
                                if temp_b == temp_d:
                                    _current_bit = temp_d
                                else:
                                    _current_bit = 2
                    index += 1
                    continue
                token = ('ELSE', else_block)
            elif len(else_block) == 0:
                if token[0] == 'IF_ELSE':
                    if is_loop(if_block):
                        _current_bit = if_temp
                        output.extend(if_block)
                        index += 1
                        continue
                    token = ('IF', if_block)
                else:
                    temp_b, temp_c = optimize(token[3], amount, rearrange, _current_bit=_current_bit)
                    if _current_bit in (1,2):
                        temp_a, temp_d = optimize(token[1], amount, rearrange, _current_bit=temp_c)
                    if _current_bit == 1:
                        output.extend(temp_b)
                        output.extend(temp_a)
                        _current_bit = temp_d
                    elif _current_bit == 0:
                        output.extend(temp_b)
                        _current_bit = temp_c
                    else:
                        output.append((token[0],temp_a,[],temp_b))
                        _current_bit = temp_d
                    index += 1
                    continue
            else:
                if token[0] == 'IF_ELSE_SPECIAL':
                    starts, temp = optimize(token[3], amount, rearrange, _current_bit=_current_bit)
                    if _current_bit in (1, 2):
                        if_block, temp_a = optimize(if_block, amount, rearrange, _current_bit=temp)
                    else:
                        if_block = []
                    if _current_bit in (0, 2):
                        else_block, temp_b = optimize(else_block, amount, rearrange, _current_bit=temp)
                    else:
                        else_block = []
                    if _current_bit == 0:
                        else_block, temp_b = optimize(starts+else_block, amount, rearrange, _current_bit=0)
                        _current_bit = temp_b
                        output.extend(else_block)
                        index += 1
                        continue
                    elif _current_bit == 1:
                        else_block, temp_a = optimize(starts+if_block, amount, rearrange, _current_bit=1)
                        _current_bit = temp_a
                        output.extend(if_block)
                        index += 1
                        continue
                    elif temp_a == temp_b:
                        _current_bit = temp_a
                else:
                    if is_loop(if_block):
                        _current_bit = 0
                        output.extend(if_block)
                    if _current_bit == 0:
                        _current_bit = else_temp
                        output.extend(else_block)
                        index += 1
                        continue
                    elif _current_bit == 1:
                        _current_bit = if_temp
                        output.extend(if_block)
                        index += 1
                        continue
                    if if_temp == else_temp:
                        _current_bit = if_temp
                    else:
                        _current_bit = 2
                    starts = []
                repeats = []
                for a, b in zip(if_block[::-1],else_block[::-1]):
                    if a != b:
                        break
                    repeats.append(a)
                if repeats:
                    repeats_length = len(repeats)
                    if_index = len(if_block) - repeats_length
                    else_index = len(else_block) - repeats_length
                    if_block = if_block[:if_index]
                    else_block = else_block[:else_index]
                for a, b in zip(if_block, else_block):
                    if a != b:
                        break
                    starts.append(a)
                if repeats:
                    if starts:
                        starts_length = len(starts)
                        if token[0] == 'IF_ELSE_SPECIAL':
                            starts_length -= len(token[3])
                        if_block = if_block[starts_length:]
                        else_block = else_block[starts_length:]
                        special_block = starts
                        output.append(('IF_ELSE_SPECIAL', if_block, else_block, special_block))
                    else:
                        output.append(('IF_ELSE',if_block, else_block))
                    output.extend(repeats)
                    index += 1
                    continue
          