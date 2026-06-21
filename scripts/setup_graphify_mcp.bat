@echo off
REM graphify MCP setup — run once to install MCP support
REM After this, restart Claude Desktop/Code to pick up the new MCP server

echo === graphify MCP Setup ===
echo.

REM 1. Install MCP extra
echo [1/2] Installing graphifyy[mcp]...
uv tool install --upgrade "graphifyy[mcp]"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install graphifyy[mcp]. Try manually: uv tool install --upgrade "graphifyy[mcp]"
    exit /b 1
)
echo Done.

REM 2. Verify MCP server starts
echo [2/2] Verifying MCP server...
python -c "from graphify.serve import serve; print('MCP server module OK')"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: MCP module not available
    exit /b 1
)
echo Done.

echo.
echo === Setup complete ===
echo The graphify MCP server is configured in:
echo   C:\Users\Admin\AppData\Roaming\Claude\claude_desktop_config.json
echo.
echo Restart Claude Desktop/Code to activate.
echo Test with: /graphify query "show me god nodes"
