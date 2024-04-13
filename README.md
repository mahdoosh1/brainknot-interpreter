This is a Brainknot interpreter written in Python.

Usage:
 Open file with python by double clicking.
 or use `python3 brainknot.py` in order to run the code

You can use it as a module as well:
```python
  from brainknot import brainknot

  sourcecode = """
    xor:[>[>*<,><]] xor xor xor
  """

  inputs = "011011"

  out = brainknot(sourcecode,inputs)
  print(out)
```
[Brainknot Main Repository](github.com/mahdoosh1/brainknot)
[Previous Repository](github.com/mahdoosh1/Python-Brainknot)
