#!/usr/bin/env python3
"""Fabrication outputs and 3D renders of the board, through KiCad's MCP server (board jobs)."""
from mcp_client import KiCad

k = KiCad()
pcb = [d for d in k.tool('kicad_status')['open_documents'] if d['type'] == 'DOCTYPE_PCB'][0]
OUT = pcb['project']['path'].rstrip('/') + '/'
L = lambda v: {'x_nm': v, 'y_nm': v, 'z_nm': v}
job = lambda path: {'document': pcb, 'output_path': OUT + path}

# The Uno template plots only copper and silkscreen; a fab needs mask, paste and the outline too
LAYERS = ['BL_F_Cu', 'BL_B_Cu', 'BL_F_SilkS', 'BL_B_SilkS', 'BL_F_Mask', 'BL_B_Mask',
          'BL_F_Paste', 'BL_B_Paste', 'BL_Edge_Cuts']
plot = k.api('GetBoardPlotSettings', board=pcb)['plot_settings']
plot['layers'] = LAYERS
print('plot settings', k.api('SetBoardPlotSettings', board=pcb, plot_settings=plot))

print('gerbers', k.api('RunBoardJobExportGerbers', job_settings=job('fab/'),
                       use_board_plot_params=True, create_gerber_job_file=True))
print('drill', k.api('RunBoardJobExportDrill', job_settings=job('fab/'), format='DF_EXCELLON',
                     units='U_MM', origin='DO_ABSOLUTE', map_format='DMF_PDF'))
for side in ('RS_TOP', 'RS_BOTTOM'):
    name = 'render-%s.png' % side[3:].lower()
    print(name, k.api('RunBoardJobExportRender', job_settings=job(name), format='RF_PNG',
                      quality='RQ_HIGH', background_style='RBS_OPAQUE', width=1600, height=1200,
                      side=side, zoom=1.0, use_board_stackup_colors=False,
                      procedural_textures=True, anti_alias=True, post_process=True,
                      # unset lights are 0 (black); these are kicad-cli's defaults
                      light_top_intensity=L(0.0), light_bottom_intensity=L(0.0),
                      light_side_intensity=L(0.5), light_camera_intensity=L(0.3),
                      light_side_elevation=60))
