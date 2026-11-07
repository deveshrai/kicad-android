#!/usr/bin/env python3
"""Point the board's 3D model paths at the models copied into the project, via KiCad's MCP server.

KiCad Android does not bundle the 3D model library (several GB).  The models this board uses are
copied into <project>/3dmodels, and project text variables named like the path variables point
there; KiCad resolves ${KICAD10_3DMODEL_DIR} from project text variables before the environment.
"""
from mcp_client import KiCad

k = KiCad()
PRJ = {'name': 'esp32s3-uno', 'path': '/storage/emulated/0/Download/esp32s3-uno/'}
DOC = {'type': 'DOCTYPE_PROJECT', 'project': PRJ}
models = '${KIPRJMOD}/3dmodels'
print(k.api('SetTextVariables', document=DOC, merge_mode='MMM_MERGE',
            variables={'variables': {'KICAD10_3DMODEL_DIR': models,
                                     'KICAD9_3DMODEL_DIR': models}}))
print(k.api('GetTextVariables', document=DOC))
print(k.api('ExpandTextVariables', document=DOC,
            text=['${KICAD10_3DMODEL_DIR}/RF_Module.3dshapes/ESP32-S3-WROOM-1.step']))
