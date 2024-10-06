import ast
import os
from collections import defaultdict

class APIFunctionDependencyAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.current_function = None
        self.api_routes = defaultdict(list)  # Track API routes and their functions
        self.function_calls = defaultdict(list)  # Track function calls in each function
        self.function_definitions = []  # Track defined functions
        self.current_route = None  # Track the current API route

    def visit_FunctionDef(self, node):
        # Record function name
        self.current_function = node.name
        self.function_definitions.append(node.name)
        
        # If a function is part of an API route, add it to the route
        if self.current_route:
            self.api_routes[self.current_route].append(node.name)
        
        # Visit the function body
        self.generic_visit(node)
        self.current_function = None

    def visit_Call(self, node):
        # Record function calls within the current function
        if isinstance(node.func, ast.Name) and self.current_function:
            self.function_calls[self.current_function].append(node.func.id)
        self.generic_visit(node)

    def visit_Expr(self, node):
        # Look for API route decorators (e.g., @app.route or @router.get)
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute):
            decorator_name = node.value.func.attr  # Capture the decorator name (e.g., "route", "get")

            # Detect API routes (Flask-style or FastAPI-style)
            if decorator_name in ["route", "get", "post", "put", "delete", "patch"]:
                # Ensure that the decorator has at least one argument (the API path)
                if len(node.value.args) > 0 and isinstance(node.value.args[0], ast.Str):
                    self.current_route = node.value.args[0].s  # Extract the API route (path)
                else:
                    self.current_route = None  # Handle cases where no argument is passed (or not a string)
        else:
            self.current_route = None  # Reset route when not inside a valid decorator

        self.generic_visit(node)

def analyze_files_in_folder(folder_path):
    analyzer = APIFunctionDependencyAnalyzer()
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as source_file:
                    source_code = source_file.read()
                    try:
                        # Parse the file and analyze dependencies
                        tree = ast.parse(source_code)
                        analyzer.visit(tree)
                    except SyntaxError as e:
                        print(f"Skipping {file_path}, invalid syntax")
    return analyzer

def print_api_dependency_tree(analyzer):
    # Print the API routes and their function dependencies
    for api_route, functions in analyzer.api_routes.items():
        print(f"API Route: {api_route}")
        for function in functions:
            print(f"    |-- {function}")
            print_dependency_tree(analyzer, function, depth=2)

def print_dependency_tree(analyzer, function, depth=1, visited=None):
    if visited is None:
        visited = set()
    
    if function in visited:
        print("    " * depth + "|-- [Cyclic Dependency] --> " + function)
        return
    
    visited.add(function)

    # Recursively print the functions it calls
    for called_function in analyzer.function_calls.get(function, []):
        if called_function in analyzer.function_definitions:
            print("    " * depth + "|-- " + called_function)
            print_dependency_tree(analyzer, called_function, depth + 1, visited)

if __name__ == "__main__":
    folder_path = "./app"  # Specify your folder path here
    analyzer = analyze_files_in_folder(folder_path)
    
    # Print API routes and their dependencies
    print_api_dependency_tree(analyzer)
