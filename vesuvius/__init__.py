import os
import sys
import site

def check_agreement():
    install_path = site.getsitepackages()[1]
    agreement_file_path = os.path.join(install_path, 'vesuvius', 'setup', 'agreement.txt')

    # Get the name of the currently running script
    current_script = os.path.abspath(sys.argv[0])

    # Check if the current script is not the setup script
    if not os.path.exists(agreement_file_path):
        if "accept_terms" not in current_script:
            raise ImportError("You must accept the terms and conditions before using this package. Run `accept_terms.py`.")
    else:   
        with open(agreement_file_path, 'r') as file:
            content = file.read().strip()
            if content != 'yes':
                raise ImportError("The agreement file is corrupted or incorrect. Please run `accept_terms.py` again.")

# Check agreement on import
check_agreement()