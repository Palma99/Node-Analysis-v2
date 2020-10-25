import re
import numpy as np
from collections import OrderedDict

# Ask user for netlist name
# while True:
#     print('\n' + '-' * 70)
#     file_name = input("Nome della netlist (Il file .net deve essere nella cartella corrente): ")
#     file_name = file_name.replace('.net', '')
#     try:
#         netlist_file = open(file_name + '.net', 'r')
#         break
#     except:
#         print('\nErrore nell\'apertura del file. Assicurati che il nome sia giusto e che sia nella cartella corrente.')


# Just for testing
netlist_file = open('netlist.net', 'r')

# Read data from netlist file line by line
content = netlist_file.readlines()

# --------- Processing and clear the netlist ---------

# Remove leading and trailing white space
content = [x.strip() for x in content]  

# Remove empty lines
while '' in content:
    content.pop(content.index(''))

# Remove Spice notation N00...
i = 0
for s in content:
    content[i] = re.sub(r'N0+', '', s)
    i += 1

# Remove comment lines, these start with a asterisk *
content = [n for n in content if not n.startswith('*')]

# Remove other comment lines, these start with a semicolon ;
content = [n for n in content if not n.startswith(';')]

# Remove spice directives, these start with a period, .
content = [n for n in content if not n.startswith('.')]

# Converts 1st letter to upper case
content = [x.capitalize() for x in content]

# Removes extra spaces between entries
content = [' '.join(x.split()) for x in content]


# Add support for Internetional System Prefixes
prefixes = {
    'k': '10**3',
    'm': '10**-3',
    'μ': '10**-6',
    'n': '10**-9',
    'f': '10**-15',
    'p': '10**-12',
    'd': '10**-1',
    'c': '10**-2'
}

i = -1
for s in content:
    i += 1
    # Get value of component
    value = s.split(' ')[3]
    for pre in prefixes:
        # Check if value contains a prefix
        if pre in value:
            value = value.replace(pre, '*' + prefixes[pre])
            value = str(eval(value))
            break

    s1 = content[i].split(' ')[:3]
    content[i] = ' '.join(s1) + ' ' + value


# Get a list nodes of the circuit and number of voltage sources
n_sources = 0
nodes = set() # Set will contain unique elements

for component in content:
    data = component.split(' ')
    nodes.add(data[1])
    nodes.add(data[2])
    if data[0][0] == 'V':
        n_sources += 1


# Remove ground node from nodes set and convert nodes to an array
nodes.remove('0')
nodes = list(nodes)

# Number of nodes
nodes_count = len(nodes)

# Matrixes
A_size = (n_sources + nodes_count, n_sources + nodes_count)
G_size = (nodes_count, nodes_count)
B_size = (nodes_count, n_sources)
C_size = (n_sources, nodes_count)
D_size = (n_sources, n_sources)
X_size = (nodes_count + n_sources, 1)
v_size = (nodes_count, 1)
j_size = (n_sources, 1)

A = np.zeros(A_size)
G = np.zeros(G_size)
B = np.zeros(B_size)
C = np.zeros(C_size)
D = np.zeros(D_size)
X = np.empty(X_size[0], dtype=object)
Z = np.zeros(X_size)

v = np.zeros(v_size)
j = np.zeros(j_size)

I = np.zeros(v_size)
e = np.zeros(j_size)


# Keep track number of sources
source_counter = 0

for component in content:
    data = component.split(' ')

    positive_node = int(data[1])
    negative_node = int(data[2])

    # Build G matrix
    if data[0][0] == 'R':

        g = 1 / float(data[3]) # Calculate conductance of the resistor

        # If not connected to ground
        if (positive_node != 0) and (negative_node != 0):
            G[positive_node - 1, negative_node - 1] -= g
            G[negative_node - 1, positive_node - 1] -= g

        # If it's connected to ground, add element to diagonal of matrix
        if positive_node != 0:
            G[positive_node - 1, positive_node - 1] += g

        if negative_node != 0:
            G[negative_node - 1, negative_node - 1] += g

    # Build B matrix
    elif data[0][0] == 'V':
        # Fill e matrix
        e[source_counter] = float(data[3])

        if positive_node != 0:
            B[positive_node - 1, source_counter] = 1
        
        if negative_node != 0:
            B[negative_node - 1, source_counter] = -1

        source_counter += 1

    elif data[0][0] == 'I':
        if positive_node != 0:
            I[positive_node - 1] -= float(data[3])
        if negative_node != 0:
            I[negative_node - 1] += float(data[3])


# Transpose B matrix to get C
C = np.transpose(B)

# Z is [i e]. Contains indipendent sources values
Z = np.row_stack((I, e))

# Fill X matrix contains symbols

X[0:len(nodes)] = ['v_' + str(n) for n in nodes] # Fill with nodes

v_sources = ['i_' + vs.split(' ')[0] for vs in content if vs[0] == 'V']

X[len(nodes):] = v_sources # Fill with currents of voltage source 

# Build A matrix as a composition of G B C D
first_A_row = np.column_stack((G, B))
second_A_row = np.column_stack((C, D))
A = np.row_stack((first_A_row, second_A_row))

# Solve matrix system
rs = np.linalg.solve(A, Z)

# Print sorted output
output_values = {}

i = 0
for v in rs:
    output_values[X[i]] = str(float(v))
    i += 1

output_values = OrderedDict(sorted(output_values.items(), key=lambda t: t[0]))

for out in output_values:
    print(out + ' = ' + output_values[out])