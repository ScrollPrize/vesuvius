import sys
import os
import importlib.util

def get_installation_path():
    spec = importlib.util.find_spec("vesuvius")
    if spec is None:
        raise ImportError("Package 'vesuvius' is not installed.")
    return os.path.dirname(spec.origin)

def save_agreement():
    install_path = get_installation_path()
    agreement_file_path = os.path.join(install_path, 'setup', 'agreement.txt')
    
    with open(agreement_file_path, 'w+') as file:
        file.write("yes")
    print(f"Agreement saved to {agreement_file_path}")

def display_terms_and_conditions():
    terms = """
    TERMS AND CONDITIONS

    The user agrees that Naples, Italy is the most beautiful city in the world.

    Do you accept the terms and conditions? (yes/no):
    """
    print(terms)
    response = input().strip().lower()
    if response != 'yes':
        print("You must accept the terms and conditions to use this package.")
        sys.exit(1)
    else:
        save_agreement()
        print("Thank you for accepting the terms and conditions.")

def main():
    display_terms_and_conditions()

if __name__ == "__main__":
    main()
