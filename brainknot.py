import warnings
from PIL import Image
from ast import literal_eval
VALID_FUNC_CHARS = tuple("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_.")

def backslash_handler(text, end_char):
    b = 0
    out = ''
    for idx, i in enumerate(text):
        if i == end_char and b == 0:
            return out, idx
        if i == '\\':
            if b:
                out += i
            b = 1 - b
        else:
            if b:
              try:
                i = eval('"\\'+i+'"')
              except:
                pass
            out += i
            b = 0

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
def optimize_space(code):
    replaces = []
    k = ""
    j = ""
    for i in code:
        if j == " ":
            if i not in VALID_FUNC_CHARS:
                if k not in VALID_FUNC_CHARS:
                    if k:
                        replaces.append((k,i))
        k = j
        j = i
    for i in replaces:
        a, b = i
        s, n = a+b, a+" "+b
        code = code.replace(n, s)
    return code
def simple_optimize(code):
    code = optimize_space(code)
    while True:
        condition = "**" in code
        condition |= "[]" in code
        condition |= ",]" in code
        condition |= "*-" in code
        condition |= "*>" in code
        condition |= "  " in code
        if not condition:
            break
        code = code.replace("**","")
        code = code.replace("[]","")
        code = code.replace(",]","]")
        code = code.replace("*-","-")
        code = code.replace("*>",">")
        code = code.replace("  "," ")
    return code

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
                comma = find_loc(code,index,",")
                if comma:
                    next_comma = find_loc(code,comma,",")
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

def lexer(code):
    code = simple_optimize(code)
    code = convert_3rd_if(code)
    code = simple_optimize(code)
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
        if char == "/":
            comment = not comment
        elif char == "{":
            print_statement = True
            handle = backslash_handler(code[index+1:],"}")
            if handle is None:
                raise SyntaxError("Print statement is not terminated")
            token, index = handle
            tokens.append(("PRINT",token))
        elif not (comment or print_statement):
            if if_depth == 0 and loop_depth == 0:
                if char in VALID_FUNC_CHARS:
                    if not func_name:
                        func_name = ""
                    func_name += char
                elif func_name:
                    is_stack_number = False
                    if func_name[0].isdigit() and func_name not in ("_","."):
                        is_stack_number = all(i in "0123456789" for i in func_name)
                        if not is_stack_number:
                            raise SyntaxError("Function name cannot start with underline, dot, or a digit")
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
                elif if_depth == 0 and loop_depth == 0:
                    def_start = index+1
                    index = find_loc(code,index,"]")
                    if not index:
                        raise SyntaxError("Function definition didn't finish")
                    token = ("DEF",lexer(code[def_start:index]))
                    tokens.append(token)
            elif char == "," and if_depth == 1 and loop_depth == 0:
                else_start = index
            elif char == "]":
                if if_depth == 0:
                    raise SyntaxError("if ended outside its statement")
                if not last_was_if.pop():
                    raise SyntaxError("If ended inside a loop")
                if_depth -= 1
                if loop_depth == 0 and if_depth == 0:
                    if else_start is None:
                        if_segment = code[if_start+1:index]
                        token = ("IF", lexer(if_segment))
                    elif else_start != (if_start +1):
                        if_segment = code[if_start+1:else_start]
                        else_segment = code[else_start+1:index]
                        token = ("IF_ELSE", lexer(if_segment), lexer(else_segment))
                    else:
                        else_segment = code[else_start+1:index]
                        token = ("ELSE",lexer(else_segment))
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
                    token = ("DEF_EXEC",lexer(code[def_start:index]))
                    tokens.append(token)
            elif char == ")":
                if loop_depth == 0:
                    raise SyntaxError("loop ended outside its statement")
                if last_was_if.pop():
                    raise SyntaxError("loop ended inside an if statement")
                loop_depth -= 1
                if if_depth == 0 and loop_depth == 0:
                    loop_segment = code[loop_start+1:index]
                    token = ("LOOP",lexer(loop_segment))
                    tokens.append(token)
            if if_depth == 0 and loop_depth == 0:
                if char in "0123456789":
                   if not stack_number:
                       stack_number = ""
                   stack_number += char
                elif stack_number:
                    tokens.append(("STACK",int(stack_number)))
                    stack_number = None
                elif char == ">":
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
    return tokens

def parser(tokens):
    new_tokens = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index == 0:
            new_tokens.append(token)
            index += 1
            last_token = list(token)
            continue
        if last_token[0] == token[0] and token[0] in ("RUN","PRINT","LOOP"):
            if token[0] == "LOOP":
                warnings.warn(SyntaxWarning("Using two adjacent loops is useless because second loop will never run"))
                index += 1
                last_token = list(token)
                continue
            last_token[1] += token[1]
            token = tuple(last_token)
            new_tokens[-1] = token
        else:
            if token[0] == "IF_ELSE":
                token = ("IF_ELSE",parser(token[1]),parser(token[2]))
            elif token[0] in ("DEF", "DEF_EXEC", "IF", "LOOP","ELSE"):
                token = (token[0],parser(token[1]))
            new_tokens.append(token)
        index += 1
        last_token = list(token)
    return new_tokens

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
    depth = [["ROOT",0]]
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
        valid, temp = get_token(depth)
        if not valid:
            name = temp
            if name == "LOOP":
                token = ("RELOOP",)
            elif name == "ROOT":
                token = ("HALT",)
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
                depth.pop(0)
                depth.pop(0)
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
    parsed = parser(lexed)
    evaluated = evaluator(parsed,inputs)
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
            p = parser(l)
            pp(p)
            print()
            e = evaluator(p, inputs)
            print(e[0])
            print()
        except Exception as e:
            print(repr(e))
        prev = code

if __name__ == "__main__":
    main()