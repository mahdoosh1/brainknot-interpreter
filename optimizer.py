import brainknot

b = '>[[,*](<),<]'
a = brainknot.lexer(b, optimize_=False)
a = brainknot.optimize(a, amount=1)
b = brainknot.decompile(a)
print(b)