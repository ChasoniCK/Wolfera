# This is a very useful piece of software

"""
    This is a multi-line comment test
    with asterisks in it *******
    Amazing!
"""

def oopify(prefix):
    return prefix + "oop"


def join(elements, separator):
    result = ""
    len_ = len(elements)

    for i in range(len_):
        result = result + elements[i]
        if i != len_ - 1:
            result = result + separator

    return result


def map_func(elements, func):
    new_elements = []

    for element in elements:
        new_elements.append(func(element))

    return new_elements


print("Greetings universe!")

for i in range(6):
    print(join(map_func(["l", "sp"], oopify), ", "))
