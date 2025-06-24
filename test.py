import unittest
import brainknot

class TestOptimizer(unittest.TestCase):
    def test_optimizer(self):
        lexed = brainknot.lexer(">[>*<,><]")
        self.assertEqual(lexed, [('INPUT',), ('IF_ELSE_SPECIAL', [('FLIP',)], [], [('INPUT',)]), ('OUTPUT',)])
    def test_optimizer_hard(self):
        lexed = brainknot.lexer(">[[,*](<),<]", optimize_=True)
        self.assertEqual(lexed, [('INPUT',), ('LOOP', [('OUTPUT',)]), ('OUTPUT',)])

if __name__ == '__main__':
    unittest.main()