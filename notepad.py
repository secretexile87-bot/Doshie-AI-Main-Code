#!/usr/bin/env python3
import os
import sys

def create_file(filename):
    with open(filename, 'w') as file:
        file.write('')
    print(f'File {filename} created.')

def read_file(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            print(file.read())
    else:
        print(f'File {filename} does not exist.')

def update_file(filename, content):
    if os.path.exists(filename):
        with open(filename, 'w') as file:
            file.write(content)
        print(f'File {filename} updated.')
    else:
        print(f'File {filename} does not exist.')

def delete_file(filename):
    if os.path.exists(filename):
        os.remove(filename)
        print(f'File {filename} deleted.')
    else:
        print(f'File {filename} does not exist.')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python notepad.py <command> <filename> [content]')
    else:
        command = sys.argv[1]
        filename = sys.argv[2]
        if len(sys.argv) > 3:
            content = ' '.join(sys.argv[3:])
        else:
            content = None
        if command == 'create':
            create_file(filename)
        elif command == 'read':
            read_file(filename)
        elif command == 'update':
            update_file(filename, content)
        elif command == 'delete':
            delete_file(filename)
        else:
            print('Invalid command. Use create, read, update, or delete.')