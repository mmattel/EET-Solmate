import sys
import io

# get all available python modules that can be included
stdout_sys = sys.stdout
stdout_capture = io.StringIO()
sys.stdout = stdout_capture
help('modules')
sys.stdout = stdout_sys
help_out = stdout_capture.getvalue()
# Remove extra text from string
help_out = help_out.replace('.', '')
help_out = help_out.replace('available modules', '%').replace('Enter any module', '%').split('%')[-2]
# Split multicolumn output
help_out = help_out.replace('\n', '%').replace(' ', '%').split('%')
help_out = list(filter(None, help_out))
help_out.sort()
# remove all items starting with '_'
all_modules = [x for x in help_out if not x.startswith('_')]

with open('requirements.txt', 'r') as f:
	requirements = f.read().split('\n')

# remove empty
requirements = ' '.join(requirements).split()

# remove all items starting with '#'
requirements = [x for x in requirements if not x.startswith('#')]

# uncomment for testing
#print(requirements)
#print(all_modules)

# get all modules that are already installed and do not need to be in requirements
match = list(set(requirements).intersection(all_modules))
print()
print('The following modules can be commented in requirements.txt because already available:')
print()
print(match)
print()
print('When done, call: python -m pip install -r requirements.txt')
print()
