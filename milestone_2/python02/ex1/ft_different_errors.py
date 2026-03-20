#!/usr/bin/env python3
def garden_operations():
    temp_str = 'abc'
    temp_int = 25
    my_dict = {'a': 1, 'b': 2}
    print("Testing ValueError...")
    try:
        temp = int(temp_str)
    except ValueError:
        print("Caught ValueError: invalid literal for int()\n")
    print("Testing ZeroDivisionError...")
    try:
        _ = temp_int / 0
    except ZeroDivisionError:
        print("Caught ZeroDivisionError: division by zero\n")
    print("Testing FileNotFoundError...")
    try:
        f = open('non_existent_file.txt', 'r')
        f.close()
    except FileNotFoundError:
        print("Caught FileNotFoundError: No such file 'missing.txt'\n")
    print("Testing KeyError...")
    try:
        print(my_dict['c'])
    except KeyError:
        print("Caught KeyError: 'missing_plant'\n")
    print("Testing multiple errors together...")
    try:
        temp = int(temp_str)
        _ = temp / 0
        open('non_existent_file.txt', 'r')
        print(my_dict['c'])
    except (ValueError, ZeroDivisionError, FileNotFoundError, KeyError):
        print("Caught an error, but program continues!\n")


def test_garden_operations():
    print("=== Garden Error Types Demo ===\n")
    garden_operations()
    print("All error types tested successfully!")


if __name__ == "__main__":
    test_garden_operations()
