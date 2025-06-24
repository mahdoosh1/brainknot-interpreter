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
    code = convert_3rd_if(code)
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
                        else_segment = code[else_start+1:special_start] # type: ignore
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
            if _current_bit < 2: # type: int
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
            if temp == 1:
                # raise RuntimeError("Loop never breaks")
                pass
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
            else_block, else_temp = optimize(token[2], amount, rearrange, _current_bit=0) # type: ignore
            if len(if_block) == 0:
                if len(else_block) == 0 or token[0] == 'IF_ELSE_SPECIAL':
                    if token[0] == 'IF_ELSE_SPECIAL':
                        if len(else_block) == 0:
                            temp, _current_bit = optimize(token[3], amount, rearrange, _current_bit=_current_bit) # type: ignore
                            output.extend(temp)
                        else:
                            temp_b, temp_c = optimize(token[3], amount, rearrange, _current_bit=_current_bit) # type: ignore
                            if _current_bit in (0, 2):
                                temp_a, temp_d = optimize(token[2], amount, rearrange, _current_bit=temp_c) # type: ignore
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
                    temp_b, temp_c = optimize(token[3], amount, rearrange, _current_bit=_current_bit) # type: ignore
                    if _current_bit in (1,2):
                        temp_a, temp_d = optimize(token[1], amount, rearrange, _current_bit=temp_c) # type: ignore
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
                    starts, temp = optimize(token[3], amount, rearrange, _current_bit=_current_bit) # type: ignore
                    if _current_bit in (1, 2):
                        if_block, temp_a = optimize(if_block, amount, rearrange, _current_bit=temp)
                    else:
                        if_block = []
                    if _current_bit in (0, 2):
                        else_block, temp_b = optimize(else_block, amount, rearrange, _current_bit=temp) # type: ignore
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
                    elif temp_a == temp_b: # type: ignore
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
                    starts.append(a) # type: ignore
                if repeats:
                    if starts:
                        starts_length = len(starts)
                        if token[0] == 'IF_ELSE_SPECIAL':
                            starts_length -= len(token[3]) # type: ignore
                        if_block = if_block[starts_length:]
                        else_block = else_block[starts_length:]
                        special_block = starts
                        output.append(('IF_ELSE_SPECIAL', if_block, else_block, special_block))
                    else:
                        output.append(('IF_ELSE',if_block, else_block))
                    output.extend(repeats)
                    index += 1
                    continue
                if starts:
                    starts_length = len(starts)
                    if token[0] == 'IF_ELSE_SPECIAL':
                        starts_length -= len(token[3]) # type: ignore
                    if_block = if_block[starts_length:]
                    else_block = else_block[starts_length:]
                    special_block = starts
                    output.append(('IF_ELSE_SPECIAL', if_block, else_block, special_block))
                    index += 1
                    continue
                token = ('IF_ELSE', if_block, else_block)
        elif token[0] == 'STACK':
            if token[1] == current_stack:
                index += 1
                continue
            current_stack = token[1]
        elif token[0] == 'PUSH':
            next_token = get_next_token(index)
            if next_token[0] == 'POP':
                index += 2
                continue
        elif token[0] == 'PRINT':
            next_token = get_next_token(index)
            if next_token[0] == 'PRINT':
                token = (token[0], token[1]+next_token[1]) # type: ignore
                output.append(token)
                index += 2
                continue
        output.append(token)
        index += 1
    if amount > 1:
        for _ in range(amount-1):
            new_output = optimize(output, 1, rearrange, _current_bit=original_current_bit)
            if not (original_current_bit == -1):
                new_output = new_output[0]
            if new_output == output:
                break
            output = new_output
    if original_current_bit != -1:
        return output, _current_bit
    return output

class FormatError(SyntaxError):
    pass

def validate(tokens):
    if isinstance(tokens, list) or isinstance (tokens, tuple):
        for token in tokens:
            if len(token) == 0:
                raise FormatError("Detected empty token")
            if not isinstance(token[0], str):
                raise FormatError("Detected non-string name for token")
            if len(token) > 1:
                if token[0] in ("FUNC_NAME", "PRINT"):
                    if not isinstance(token[1], str):
                        raise FormatError("Detected non-string parameter for FUNC_NAME or PRINT")
                    continue
                for new_tokens in token[1:]:
                    validate(new_tokens)
        return
    raise FormatError("Non iterable tokens")

def decompile(tokens):
    output = []
    direct_copy = {
        'INPUT': '>',
        'OUTPUT': '<',
        'POP': '-',
        'PUSH': '+',
        'POPPUSH': '~',
        'FLIP': '*',
        'PSTACK': '_',
        'BREAK': '.',
        'PIXEL': '^',
        'LINE': '\\',
        'FRAME': ';'
    }
    for token in tokens:
        if token[0] == 'PRINT':
            output.append('{'+token[1]+'}')
        elif token[0] == 'FUNC_NAME':
            output.append(' '+token[1])
        elif token[0] == 'DEF':
            output.append(':['+decompile(token[1])+']')
        elif token[0] == 'DEF_EXEC':
            output.append(':('+decompile(token[1])+')')
        elif token[0] == 'IF':
            output.append('['+decompile(token[1])+']')
        elif token[0] == 'ELSE':
            output.append('[,'+decompile(token[1])+']')
        elif token[0] == 'IF_ELSE':
            output.append('['+decompile(token[1])+','+decompile(token[2])+']')
        elif token[0] == 'IF_ELSE_SPECIAL':
            output.append('['+decompile(token[1])+','+decompile(token[2])+','+decompile(token[3])+']')
        elif token[0] == 'LOOP':
            output.append('('+decompile(token[1])+')')
        elif token[0] == 'STACK':
            output.append(' '+str(token[1]))
        else:
            output.append(direct_copy[token[0]])
    return ''.join(output)

def evaluator(tokens,inputs=None):
    if inputs is None:
        inputs = []
    if isinstance(inputs, str):
        inputs = inputs[::-1]
    if isinstance(tokens, str):
        tokens = literal_eval(tokens)
        validate(tokens)
    input_stack = list(map(int,inputs))
    output_stack = []
    memory_stack = [[0] * 256] * 256  # Adjust stack size as needed

    # Current memory pointer and bit
    mem_ptr = [0, [0]*256]
    current_bit = 0
    # Function address table and return stack
    funcs = {} # name : depth
    # Image Buffer
    current_screen = Image.new('L',(64,64),color=127)
    screen_location = [0, 0]
    frames = []
    # recursive index: [name, index]
    loop_break = 200
    loop_depth = 0
    
    depth = [["ROOT",0]]
    special = []
    def get_token(depth):
        token = tokens
        for i in depth:
            name, index = i
            if name == "CALL" and isinstance(index, str):
                token = funcs[index]
            elif index < len(token):
                token = token[index]
            else:
                return False, name
        return True, token
    while True:
        if loop_depth > loop_break:
            output_stack.append("AntiLoop break")
            break
        valid, temp = get_token(depth)
        if not valid:
            name = temp
            if name == "LOOP":
                token = ("RELOOP",)
                loop_depth += 1
            elif name == "ROOT":
                token = ("HALT",)
            elif name == "IF_ELSE_SPECIAL":  # hacky way
                depth.pop()
                should_check = depth.pop()[-1] == 3
                if should_check:
                    c_bit = special.pop()
                    if c_bit:
                        depth.append([name,1])
                    else:
                        depth.append([name,2])
                    depth.append([name, 0])
                    continue
                else:
                    token = ("BREAK",)
            else:
                # works for functions as well.
                token = ("BREAK",)
        else:
            token = temp
        op = token[0]
        if op == "INPUT":
            if len(input_stack):
                current_bit = input_stack.pop()
            else:
                op = "LOOP_BREAK"
        elif op == "OUTPUT":
            output_stack.append(current_bit)
        elif op == "PUSH":
            addr = mem_ptr[1][mem_ptr[0]]
            memory_stack[addr].append(current_bit)
            addr += 1
            mem_ptr[1][mem_ptr[0]] = addr
        elif op == "POP":
            addr = mem_ptr[1][mem_ptr[0]]
            if addr:
                current_bit = memory_stack[addr].pop()
                addr -= 1
                mem_ptr[1][mem_ptr[0]] = addr
            else:
                op = "LOOP_BREAK"
        elif op == "POPPUSH":
            addr = mem_ptr[1][mem_ptr[0]]
            if addr:
                current_bit = memory_stack[addr][-1]
            else:
                op = "LOOP_BREAK"
        elif op == "FLIP":
            current_bit = 1 - current_bit
        elif op == "PSTACK":
            addr = mem_ptr[1][mem_ptr[0]]
            if addr:
                output_stack.append(memory_stack[addr])
            else:
                output_stack.append([])
        elif op == "PIXEL":
            current_screen.putpixel(screen_location, current_bit*255)
            screen_location[0] += 1
        elif op == "LINE":
            screen_location[0] = 0
            screen_location[1] += 1
        elif op == "FRAME":
            screen_location = [0, 0]
            frames.append(current_screen)
            current_screen = Image.new("L",(64,64),color=127)
        elif op == "PRINT":
            output_stack.append(token[1])
        elif op in ("DEF", "DEF_EXEC"):
            depth[-1][1] -= 1
            valid, temp = get_token(depth)
            depth[-1][1] += 1
            if valid:
                name = temp[1]
                func_token = token[1]
                funcs[name] = func_token
                if op == "DEF_EXEC":
                    depth.append(["CALL",name])
                    depth.append(["CALL",-1])
            else:
                raise SyntaxError("Defined a function without a name behind it")
        elif op == "FUNC_NAME":
            name = token[1]
            depth[-1][1] += 1
            valid, temp = get_token(depth)
            depth[-1][1] -= 1
            if valid:
                if temp[0] not in ("DEF","DEF_EXEC"):
                    if name not in funcs:
                        raise KeyError(f"Function {name} doesn't exist")
                    depth.append(["CALL",name])
                    depth.append(["CALL",-1])
            else:
                if name not in funcs:
                    raise KeyError(f"Function {name} doesn't exist")
                depth.append(["CALL",name])
                depth.append(["CALL",-1])
        elif op == "LOOP":
            if current_bit:
                depth.append([op,1]) # go to list
                depth.append([op,-1]) # go to index
        elif op == "RELOOP":
            if len(depth) > 2:
                depth.pop()
                depth.pop()
            else:
                raise RuntimeError("Tried to end a loop which doesn't exist")
            if current_bit:
                depth[-1][1] -= 1
        elif op == "IF":
            if current_bit:
                depth.append([op,1]) # go to list
                depth.append([op,-1]) # go to index
        elif op == "IF_ELSE":
            if current_bit:
                depth.append([op,1]) # go to list
            else:
                depth.append([op,2]) # go to list
            depth.append([op,-1]) # go to index
        elif op == "IF_ELSE_SPECIAL":
            depth.append([op,3])
            depth.append([op,-1])
            special.append(current_bit)
        elif op == "ELSE":
            if not current_bit:
                depth.append([op,1]) # go to list
                depth.append([op,-1]) # go to index
        if op == "LOOP_BREAK":
            if len(depth) > 2:
                a, b = depth[-2], depth[-1]
                if a[0] == "LOOP" and b[0] == "LOOP":
                    depth.pop()
                    depth.pop()
                else:
                    raise RuntimeError("There were not enough inputs")
            else:
                raise RuntimeError("There were not enough inputs")
        if op == "BREAK":
            if len(depth) > 2:
                depth.pop() # get the index out
                depth.pop() # get the list out
            else:
                raise RuntimeError("Cannot break from an statement which doesn't exist")
        elif op == "HALT":
            break
        depth[-1][1] += 1
    output = ''.join(list(map(str,output_stack)))
    return output, frames
        
def brainknot(code, inputs=None):
    lexed = lexer(code)
    evaluated = evaluator(lexed,inputs)
    return evaluated

def pretty_print(tokens,indent=0):
    output = []
    space = " "*indent
    for token in tokens:
        if isinstance(token[-1],list):
            output.append(token[0]+":")
            for i in token[1:]:
                output.append("    "+pretty_print(i,indent+4))
                output.append("    "+"-"*(indent+4))
            output.pop()
        elif len(token) == 2:
            output.append(token[0]+"("+token[1]+")")
        else:
            output.append(token[0])
    output = ("\n"+space).join(output)
    return output

def pp(tokens):
    print(pretty_print(tokens))

def main():
    from traceback import format_exc
    prev = ""
    while True:
        code = input("code: ")
        if code.lower() in ("exit","quit"):
            break
        if code.lower().startswith("prev"):
            code = prev
        inputs = input("inputs: ")
        print()
        try:
            l = lexer(code)
            print()
            e = evaluator(l, inputs)
            print(e[0])
            print()
        except Exception as e:
            print(format_exc())
        prev = code

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()