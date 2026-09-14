import sys
import json
import traceback

try:
    from yoshi_tool_agent import execute_tool
except ImportError:
    execute_tool = None

TOOLS_REGISTRY = [
    {
        "name": "read_code_file",
        "description": "Read content from a code file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to file"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "search_code",
        "description": "Search codebase for query patterns or symbols",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "request_python_diagnostics",
        "description": "Run python diagnostics on project files",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Target file or directory"}
            }
        }
    },
    {
        "name": "consult_hermes_ai",
        "description": "Consult Hermes AI assistant sub-agent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "request_text": {"type": "string", "description": "Prompt or query for Hermes"}
            },
            "required": ["request_text"]
        }
    }
]

def respond(response):
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()

def handle_tool_call(name, args):
    if not execute_tool:
        raise RuntimeError("execute_tool could not be imported from yoshi_tool_agent.")
    return execute_tool(name, args, can_propose_changes=True)

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue

        req_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params", {})

        if method == "initialize":
            respond({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "diyoshi-core", "version": "1.0.0"}
                }
            })
        elif method == "tools/list":
            respond({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS_REGISTRY}
            })
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            try:
                res = handle_tool_call(tool_name, tool_args)
                content = [{"type": "text", "text": json.dumps(res, default=str) if isinstance(res, (dict, list)) else str(res)}]
                is_error = False
            except Exception as e:
                content = [{"type": "text", "text": f"Error: {e}\n{traceback.format_exc()}"}]
                is_error = True

            respond({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": content, "isError": is_error}
            })

if __name__ == "__main__":
    main()
