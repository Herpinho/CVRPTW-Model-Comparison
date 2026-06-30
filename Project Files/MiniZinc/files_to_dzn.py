from py_to_dzn import start_converter as python_converter
from txt_to_dzn import start_converter as txt_converter
def menu():
    option = input("""
    Select option:
                .txt (1)
                .py (2)  
    """)
    if option == "1": txt_converter()
    elif option =="2": python_converter()
    else: menu()
menu()