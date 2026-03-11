@echo off
setlocal

set URL=http://127.0.0.1:4173/figma-capture.html#figmacapture=fcf5f216-0a4c-4278-a7db-2dc213dbeec6^&figmaendpoint=https%%3A%%2F%%2Fmcp.figma.com%%2Fmcp%%2Fcapture%%2Ffcf5f216-0a4c-4278-a7db-2dc213dbeec6%%2Fsubmit^&figmadelay=1000
set OUT=c:\Users\Admin\source\repos\design-grammar-system\graph-viewer\figma-capture-preview.png

npx playwright screenshot -b chromium --channel msedge --wait-for-timeout 12000 --timeout 45000 --viewport-size 1913,911 "%URL%" "%OUT%"
