from __future__ import print_function

import tkinter as Tk_
import tkinter.ttk as ttk
from snappy.CyOpenGL import *

from snappy import Manifold

from raytracing_data import *

from sage.all import matrix

import sys

g = open('raytracing_shaders/fragment.glsl').read()

_constant_uniform_bindings = {
    'fov' : ('float', 90.0),
    'currentWeight' : ('float', 0.0),
    'maxSteps': ('int', 20),
    'maxDist': ('float', 17.4),
    'subpixelCount': ('int', 1),
    'contrast': ('float', 0.5),
    'perspectiveType': ('int', 0),
    'viewMode' : ('int', 1),
    'multiScreenShot' : ('int', 0),
    'tile' : ('vec2', [0.0, 0.0]),
    'numTiles' : ('vec2', [1.0, 1.0]),

    'gradientThreshholds' : ('float[]', [0.0, 0.25, 0.45, 0.75, 1.0]),
    'gradientColours' : ('vec3[]', [[1.0, 1.0, 1.0],
                                    [0.86, 0.92, 0.78],
                                    [0.25, 0.70, 0.83],
                                    [0.10, 0.13, 0.49],
                                    [0.0, 0.0, 0.0]]),
}

def matrix4_vec(m, p):
    return [sum([ m[i][j] * p[j] for j in range(4)])
            for i in range(4) ]

def diff(v1, v2, label = ''):
    a = sum([(x - y)**2 for x, y in zip(v1, v2) ])

    if a > 1e-10:
        print("DIFF!!!", label, v1, v2)

def check_consistency(d):
    planes = d['planes'][1]
    otherTetNums = d['otherTetNums'][1]
    entering_face_nums = d['enteringFaceNums'][1]
    SO13tsfms = d['SO13tsfms'][1]

#    verts = d['verts'][1]

#    for i in range(len(planes)/4):
#        for j in range(4):
#            for k in range(4):
#                if j != k:
#                    if abs(R31_dot(planes[4 * i + j], verts[4 * i + k])) > 1e-10:
#                        print("Bad plane equation")
    
    for i in range(len(planes)):
        if abs(R13_dot(planes[i], planes[i]) - 1) > 1e-10:
            print("Plane vec not normalized")

        plane = [-x for x in planes[i]]
        t = SO13tsfms[i]

        other_tet = otherTetNums[i]
        entering_face_num = entering_face_nums[i]
        other_plane = planes[4 * other_tet + entering_face_num]

        diff(other_plane, matrix4_vec(t, plane))
        
        check_matrix_o13(t)

def merge_dicts(*dicts):
    return { k : v for d in dicts for k, v in d.items() }

class InsideManifoldViewWidget(SimpleImageShaderWidget):
    def __init__(self, manifold, master, *args, **kwargs):

        self.manifold = manifold

        self.c = 0

        self.insphere_scale = 0.05
        self.area = 1
        self.edge_thickness = 0.005
        self.edge_thickness_cylinder = 0.005

        self._initialize_raytracing_data()

        self.num_tets = len(self.raytracing_data.mcomplex.Tetrahedra)

        self.fragment_shader_source = g.replace(
            '##num_tets##', '%d' % self.num_tets)

        SimpleImageShaderWidget.__init__(self, master, self.fragment_shader_source, *args, **kwargs)

        self.bind('<Key>', self.tkKeyPress)
        self.bind('<Button-1>', self.tkButton1)
        
        self.boost = matrix([[1.0,0.0,0.0,0.0],
                             [0.0,1.0,0.0,0.0],
                             [0.0,0.0,1.0,0.0],
                             [0.0,0.0,0.0,1.0]])

        self.tet_num = self.raytracing_data.get_initial_tet_num()

        self.view = 2
        self.perspectiveType = 0

        self.step_size = 0.1
        self.angle_size = 0.1
        self.left_translation = unit_3_vector_and_distance_to_O13_hyperbolic_translation(
            [ -1.0, 0.0, 0.0 ], self.step_size)
        self.right_translation = unit_3_vector_and_distance_to_O13_hyperbolic_translation(
            [ +1.0, 0.0, 0.0 ], self.step_size)
        self.down_translation = unit_3_vector_and_distance_to_O13_hyperbolic_translation(
            [ 0.0, -1.0, 0.0 ], self.step_size)
        self.up_translation = unit_3_vector_and_distance_to_O13_hyperbolic_translation(
            [ 0.0, +1.0, 0.0 ], self.step_size)
        self.forward_translation = unit_3_vector_and_distance_to_O13_hyperbolic_translation(
            [ 0.0, 0.0, -1.0 ], self.step_size)
        self.backward_translation = unit_3_vector_and_distance_to_O13_hyperbolic_translation(
            [ 0.0, 0.0, +1.0 ], self.step_size)

        self.left_rotation = O13_y_rotation(-self.angle_size)
        self.right_rotation = O13_y_rotation(self.angle_size)
        
        self.up_rotation = O13_x_rotation(-self.angle_size)
        self.down_rotation = O13_x_rotation(self.angle_size)
        

    def get_uniform_bindings(self, width, height):
        weights = [ 0.1 * i for i in range(4 * self.num_tets) ]

        result = merge_dicts(
            _constant_uniform_bindings,
            self.manifold_uniform_bindings,
            {
                'c' : ('int', self.c),
                'screenResolution' : ('vec2', [width, height]),
                'currentBoost' : ('mat4', self.boost),
                'weights' : ('float[]', weights),
                'tetNum' : ('int', self.tet_num),
                'viewMode' : ('int', self.view),
                'perspectiveType' : ('int', self.perspectiveType),
                'edgeThickness' : ('float', self.edge_thickness),
                'edgeThicknessCylinder' : ('float', 1.0 + self.edge_thickness_cylinder)
                })            

        check_consistency(result)

        return result

    def tkKeyPress(self, event):
        
        if event.keysym in ['0','1','2','3']:

            self.boost, self.tet_num = new_boost_and_tetnum(
                self.boost, self.tet_num, int(event.keysym))

            self.redraw_if_initialized()

        if event.keysym in ['6', '7']:
            self.c += 1;

            print(self.c)

            self.redraw_if_initialized()

        if event.keysym in ['x', 'z']:
            if event.keysym == 'x':
                s = 0.71
            if event.keysym == 'z':
                s = 1.41

            self.area *= s

            self._initialize_raytracing_data()

            self.redraw_if_initialized()

        if event.keysym == 'u':
            print(self.boost)

        if event.keysym in ['w', 'a', 's', 'd', 'e', 'c',
                            'Up', 'Down', 'Left', 'Right' ]:
                            
            if event.keysym == 'a':
                m = self.left_translation
            if event.keysym == 'd':
                m = self.right_translation
            if event.keysym == 'w':
                m = self.up_translation
            if event.keysym == 's':
                m = self.down_translation
            if event.keysym == 'e':
                m = self.forward_translation
            if event.keysym == 'c':
                m = self.backward_translation

            if event.keysym == 'Left':
                m = self.left_rotation
            if event.keysym == 'Right':
                m = self.right_rotation
            if event.keysym == 'Down':
                m = self.down_rotation
            if event.keysym == 'Up':
                m = self.up_rotation

            self.boost, self.tet_num = self.raytracing_data.fix_boost_and_tetnum(
                self.boost * m, self.tet_num)

            self.redraw_if_initialized()

        if event.keysym == 'v':
            self.view = (self.view + 1) % 3
            self.redraw_if_initialized()
            
        if event.keysym == 'n':
            self.perspectiveType = 1 - self.perspectiveType
            self.redraw_if_initialized()

    def tkButton1(self, event):
        print("tkButton1")

    def _initialize_raytracing_data(self):
        self.raytracing_data = RaytracingDataEngine.from_manifold(
            self.manifold,
            areas = self.area,
            insphere_scale = self.insphere_scale)
        
        self.manifold_uniform_bindings = (
            self.raytracing_data.get_uniform_bindings())

    def set_cusp_area(self, area):
        self.area = float(area)
        self._initialize_raytracing_data()
        self.redraw_if_initialized()

    def set_edge_thickness(self, t):
        self.edge_thickness = float(t)
        self.redraw_if_initialized()

    def set_edge_thickness_cylinder(self, t):
        self.edge_thickness_cylinder = float(t)
        self.redraw_if_initialized()        

    def set_insphere_scale(self, t):
        self.insphere_scale = float(t)
        self._initialize_raytracing_data()
        self.redraw_if_initialized()

def create_widget(manifold, toplevel):
    widget = InsideManifoldViewWidget(manifold, toplevel,
        width=600, height=500, double=1, depth=1)

    widget.make_current()
    print(get_gl_string('GL_VERSION'))
    toplevel.grid_rowconfigure(0, weight=1)
    toplevel.grid_columnconfigure(0, weight=1)
    widget.grid(row = 0, column = 0, sticky = Tk_.NSEW)

    a = ttk.Scale(toplevel, from_=0.5, to = 5,
                  orient = Tk_.HORIZONTAL,
                  command = widget.set_cusp_area)
    a.set(1)
    a.grid(row = 1, column = 0, sticky = Tk_.NSEW)

    b = ttk.Scale(toplevel, from_= 0, to = 0.03,
                  orient = Tk_.HORIZONTAL,
                  command = widget.set_edge_thickness)
    b.set(0.005)
    b.grid(row = 2, column = 0, sticky = Tk_.NSEW)
    
    c = ttk.Scale(toplevel, from_ = 0, to = 0.03,
                  orient = Tk_.HORIZONTAL,
                  command = widget.set_edge_thickness_cylinder)
    c.set(0.005)
    c.grid(row = 3, column = 0, sticky = Tk_.NSEW)

    d = ttk.Scale(toplevel, from_ = 0, to = 1.2,
                  orient = Tk_.HORIZONTAL,
                  command = widget.set_insphere_scale)
    d.set(0.05)
    d.grid(row = 4, column = 0, sticky = Tk_.NSEW)

    return widget

def main(manifold):
    root = Tk_.Tk()
    root.title('Image Shader Test')
    widget = create_widget(manifold, root)
    widget.focus_set()
    root.mainloop()
    
if __name__ == '__main__':
    print(sys.argv)

    main(Manifold(sys.argv[1]))