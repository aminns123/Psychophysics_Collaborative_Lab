
from __future__ import division
from libC import *


class Grating(stim(width=200.0, fs=10.0, ph=0.0, speed=0.0, contr=1.0, theta=0.0, bg=0.5,
                   box=False, Lbg=24.65, Lmin=0.0, Lmax=49.3, gamma=2.5, BTRR=63.2)):
    """Grating stimulus

    :param width: size of stimulus in pixels
    :param fs: spatial frequncy
    :param ph: phase
    :param speed: speed
    :param contr: contrast
    """
    frag_source = """
        //precision highp float;

        uniform float fs;
        uniform float phase;
        uniform float contr;
        uniform float bg;
        uniform float box;
        uniform float theta;
        uniform float Lbg, Lmin, Lmax, gamma, BTRR;

        vec3 lum2image(float c) {
            vec3 vout;
            float U = 255.0*pow(((1+c)*Lbg-Lmin)/(Lmax-Lmin),1.0/gamma);
            float b1 = (BTRR+1.0)/BTRR;
            //float b = min(floor(U*b1),255.0);
            float b = min(floor(U*b1),255.0) + 1.0/32.0;
            //float b2 = floor((U-b/b1)*(BTRR+1.0));
            float b2 = floor((U-b/b1)*(BTRR+1.0)) + 1.0/32.0;
            vout = vec3(b2/255.0, 0.0 ,b/255.0);
            return vout;
        }

        void main() {
            float x = gl_TexCoord[0].x - 0.5;
            float y = -(gl_TexCoord[0].y - 0.5);
            float m = exp(-0.5*(x*x + y*y)/pow(0.17,2.0));
            //float c = m*contr*cos(fs*x + phase);
            float c = m*contr*sin(fs*(x*cos(theta)+y*sin(theta)) + phase);
            if (box == 1.0) {
                gl_FragColor.rgba = vec4(lum2image(c),1.0);
            } else {
                c = bg + c/2.0;
                gl_FragColor.rgba = vec4(c,c,c,1.0);
            }
        }
        """

    def __init__(self, pos, params=Params()):
        self.pos = pos
        self.params = copy_params(self._defaults, params)
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms = dict(map(self.shader.uniform,
                                 ['fs', 'phase', 'contr', 'theta', 'bg', 'box', 'Lbg', 'Lmin', 'Lmax', 'gamma', 'BTRR']))
        glUseProgram(self.program)
        glUniform1f(self.uniforms['phase'], 0.0)
        glUniform1f(self.uniforms['fs'], self.params.fs)
        glUniform1f(self.uniforms['contr'], self.params.contr)
        glUniform1f(self.uniforms['theta'], self.params.theta)
        glUniform1f(self.uniforms['bg'], self.params.bg)
        glUniform1f(self.uniforms['box'], self.params.box)
        glUniform1f(self.uniforms['Lbg'], self.params.Lbg)
        glUniform1f(self.uniforms['Lmin'], self.params.Lmin)
        glUniform1f(self.uniforms['Lmax'], self.params.Lmax)
        glUniform1f(self.uniforms['gamma'], self.params.gamma)
        glUniform1f(self.uniforms['BTRR'], self.params.BTRR)
        glUseProgram(0)

    def draw(self):
        p = self.params
        x, y = self.pos
        w2 = p.width/2.0
        glUseProgram(self.program)
        ph = p.speed*(self.clock.time()-self.t0)
        glUniform1f(self.uniforms['phase'], ph)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)


class Rectangle(stim(width=200.0, height=200.0, theta=0.0)):
    vert_source = """
        uniform float angle;

        void main() {
            vec4 a = gl_Vertex;
            vec4 b = a;
            b.y = a.y*cos(angle) - a.z*sin(angle);
            b.z = a.z*cos(angle) + a.y*sin(angle);

            gl_TexCoord[0] = gl_MultiTexCoord0;
            gl_Position = gl_ModelViewProjectionMatrix*b;
        }"""
    frag_source = """
        uniform float fs;
        uniform float phase;

        void main() {
            float x = gl_TexCoord[0].x - 0.5;
            float y = -(gl_TexCoord[0].y - 0.5);
            float c = (1.0 + cos(fs*x + phase))/2.0;
            float m = exp(-0.5*(x*x + y*y)/pow(0.17,2.0));
            gl_FragColor.rgba = vec4(c,c,c,m);
        }
        """

    def __init__(self, pos, params=Params()):
        self.pos = pos
        self.params = copy_params(self._defaults, params)
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        self.shader = Shader(self.frag_source, self.vert_source)
        self.program = self.shader.program
        self.uniforms = dict(
            map(self.shader.uniform, ['fs', 'phase', 'angle', 'w', 'h']))
        glUseProgram(self.program)
        glUniform1f(self.uniforms['phase'], 0.0)
        glUniform1f(self.uniforms['fs'], 20.0)
        glUniform1f(self.uniforms['angle'], 0.2)
        glUseProgram(0)

    def draw(self):
        glUseProgram(self.program)
        ph = 40.0*(self.clock.time()-self.t0)
        glUniform1f(self.uniforms['phase'], ph)
        glUniform1f(self.uniforms['angle'], ph/40.0)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        w2 = self.params.width/2
        glColor3f(255.0, 0, 0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glUseProgram(0)
        glPopMatrix()


class RectangleT(stim(width=200.0, height=200.0, theta=0.0)):
    vert_source = """
        uniform float angle;

        void main() {
            vec4 a = gl_Vertex;
            vec4 b = a;
            b.y = a.y*cos(angle) - a.z*sin(angle);
            b.z = a.z*cos(angle) + a.y*sin(angle);

            gl_TexCoord[0] = gl_MultiTexCoord0;
            gl_Position = gl_ModelViewProjectionMatrix*b;
        }"""
    frag_source = """
        uniform float fs;
        uniform float phase;

        void main() {
            float x = gl_TexCoord[0].x - 0.5;
            float y = -(gl_TexCoord[0].y - 0.5);
            float c = (1.0 + cos(fs*x + phase))/2.0;
            float m = exp(-0.5*(x*x + y*y)/pow(0.17,2.0));
            gl_FragColor.rgba = vec4(c,c,c,m);
        }
        """

    def __init__(self, pos, params=Params()):
        self.pos = pos
        self.params = copy_params(self._defaults, params)
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        self.shader = Shader(self.frag_source, self.vert_source)
        self.program = self.shader.program
        self.uniforms = dict(
            map(self.shader.uniform, ['fs', 'phase', 'angle', 'w', 'h']))
        glUseProgram(self.program)
        glUniform1f(self.uniforms['phase'], 0.0)
        glUniform1f(self.uniforms['fs'], 20.0)
        glUniform1f(self.uniforms['angle'], 0.2)
        glUseProgram(0)

    def draw(self):
        glUseProgram(self.program)
        ph = 40.0*(self.clock.time()-self.t0)
        glUniform1f(self.uniforms['phase'], ph)
        glUniform1f(self.uniforms['angle'], ph/40.0)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        w2 = self.params.width/2
        glColor3f(255.0, 0, 0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glUseProgram(0)
        glPopMatrix()


class Line(stim(length=100.0, width=10.0, angle=0.0, color=(1.0, 1.0, 1.0, 1.0))):
    def __init__(self, pos, params=Params()):
        self.pos = pos
        if hasattr(params, 'color') and not iterable(params.color):
            params.color = [params.color]*3
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1, 2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.length, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

    def draw(self):
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.params.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()


class Movie(stim(fname=None, fps=60.0, scale=1.0, rotation=0.0)):
    def __init__(self, pos, params=Params()):
        self.pos = pos
        self.clock = pyglet.clock.Clock()
        self.params = copy_params(self._defaults, params)
        self.batch = pyglet.graphics.Batch()
        self.set_fname(self.params.fname)

    def set_fname(self, fname):
        im = None
        if fname:
            self.params.fname = fname
            if fname.endswith('.mat'):
                from scipy.io import loadmat
                frames = loadmat()['frames']
                h, w = frames.shape[:2]
                frames = iter(frames)
            else:
                from movieiter import ffmpegsrc
                frames, w, h = ffmpegsrc(os.path.normpath(fname))
            frm = frames.next()
            im = pyglet.image.ImageData(
                width=w, height=h, format='RGB', data=frm, pitch=-w*3)
            self.cframe = 0
            im.anchor_x = w//2
            im.anchor_y = h//2
            self.spr = pyglet.sprite.Sprite(im, batch=self.batch)
            self.spr.position = (self.pos[0], self.pos[1])
            self.spr.scale = self.params.scale
            self.spr.rotation = self.params.rotation
            self.frames = frames

        self.image = im

    def reset(self):
        self.frames, w, h = ffmpegsrc(self.params.fname)

    def draw(self):
        self.t0 = self.clock.time()
        self.draw_next()
        self.draw = self.draw_next

    def draw_next(self):
        glColor4f(255.0, 255.0, 255.0, 255.0)
        if (self.clock.time() - self.t0) > 1.0/self.params.fps:
            self.image.set_data('RGB', -self.image.width*3, self.frames.next())
            self.t0 = self.clock.time()
        if self.image:
            cx, cy = self.pos
            self.spr._group.texture = self.image.get_texture()
            self.spr.draw()


class MovieGrid(stim(fname='movie/fft.mp4', fps=29.97,
                     tilt=0.0, slant=0.0,
                     tile_image_coords=[
                         makerect(0, 0, 0.5, 1.0), makerect(0.5, 0, 0.5, 1.0)],
                     tile_disp_coords=[
                         makecrect(-200, 0, 150, 120), makerect(200, 0, 150, 120)],
                     tile_disp_anchors=[(-200, 0, 0), (200, 0, 20)],
                     tile_slants=[5, 10], tile_tilts=[10, -10], tile_colors=[0.5, 1],
                     tile_alphas=[1.0, 1.0], mask='')):
    def __init__(self, pos, params):
        self.params = copy_params(self._defaults)
        self.params.__dict__.update(params.__dict__)
        p = self.params
        # load movie
        fname = p.fname
        from movieiter import ffmpegsrc
        if not os.path.exists(fname):
            raise Exception('Movie file "%s" does not exist!' % fname)
        frames, w, h = ffmpegsrc(fname)
        frm = frames.next()
        im = pyglet.image.ImageData(
            width=w, height=h, format='RGB', data=frm, pitch=-w)
        self.tex = im.get_texture()
        rx, ry = self.tex.tex_coords[6:8]
        p.tile_image_coords = array(
            p.tile_image_coords).reshape(-1, 4, 2)*r_[rx, ry]
        p.tile_disp_coords = array(p.tile_disp_coords).reshape(-1, 4, 3)
        p.tile_disp_anchors = array(p.tile_disp_anchors).reshape(-1, 3)
        self.frames = frames
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # initialize
        N = p.tile_disp_anchors.shape[0]
        if not hasattr(p.tile_slants, '__len__'):
            p.tile_slants = [p.tile_slants]
        if not hasattr(p.tile_tilts, '__len__'):
            p.tile_tilts = [p.tile_tilts]
        if not hasattr(p.tile_colors, '__len__'):
            p.tile_colors = [p.tile_colors]
        p.tile_colors = reshape(p.tile_colors, (N, -1))
        if not hasattr(p.tile_alphas, '__len__'):
            p.tile_alphas = [p.tile_alphas]
        p.tile_alphas = reshape(p.tile_alphas, (N, -1))
        # check for shape time-series
        if hasattr(p, 'series'):
            from itertools import cycle
            Nser = p.series
            imser = array(p.tile_image_coords).reshape(Nser, -1, 4, 2)
            dsser = array(p.tile_disp_coords).reshape(Nser, -1, 4, 3)
            p.tile_image_series = [cycle(imser[i])
                                   for i in xrange(imser.shape[0])]
            p.tile_disp_series = [cycle(dsser[i])
                                  for i in xrange(dsser.shape[0])]
        self.batch, self.vlist, self.indices = make_indarray(N)
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (4*N, 3))
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4, 4))
        self.txy = from_ctypes(self.vlist.tex_coords, 'f4', (4*N, 2))
        # fill the arrays
        self.colors[...] = 1.0
        for i in xrange(N):
            self.colors[i, :, :3] = p.tile_colors[i]
            self.colors[i, :, 3] = p.tile_alphas[i]
        # self.colors[:,:,:3] = self.params.color
        for i in xrange(N):
            self.xy[i*4:(i+1)*4, :] = p.tile_disp_coords[i]
            self.txy[i*4:(i+1)*4, :] = p.tile_image_coords[i]
        # initialize mask
        self.set_mask(p.mask)
        #
        self.im = im
        self.N = N
        self.pos = pos
        # transform user-specified slants and tils from degrees to rads
        p.tile_slants = pi*array(p.tile_slants)/180.0
        p.tile_tilts = pi*array(p.tile_tilts)/180.0
        # transform each tile
        for i in xrange(self.N):
            xy = slanttilt(
                p.tile_disp_coords[i], p.tile_slants[i], p.tile_tilts[i], p.tile_disp_anchors[i])
            self.xy[i*4:(i+1)*4, :] = xy
        self.vlist._vertices_cache.invalidate()

    frag_source = """
        uniform sampler2D tex1;
        uniform sampler2D mask;
        uniform int usemask;
        uniform vec2 pixel;
        uniform vec2 offset;

        void main() {
            vec4 color1 = texture2D(tex1,gl_TexCoord[0].st);
            if (usemask == 1) {
                vec4 color2 = texture2D(mask,(gl_TexCoord[0].st-offset)*pixel);
                gl_FragColor.rgba = vec4(color1.r,color1.g,color1.b,color2.r);
            } else if (usemask < 0) {
                gl_FragColor.rgba = vec4(color1.r,color1.g,color1.b,color1.a);
            } else {
                gl_FragColor.rgba = vec4(color1.r,color1.g,color1.b,1.0);
            }
        }
        """

    def setup_shader(self):
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms = dict(
            map(self.shader.uniform, ['tex1', 'mask', 'usemask', 'pixel', 'offset']))
        # rix, riy = self.tex.tex_coords[6:8]
        rix = (self.txy[1, 0] - self.txy[0, 0])  # *rix*rix
        riy = (self.txy[2, 1] - self.txy[1, 1])
        # ax = (self.txy[1,0] - self.txy[0,0])/rix
        # ay = (self.txy[2,1] - self.txy[1,1])/riy
        # rx, ry = (ax*ax)/self.tex.width, (ay*ay)/self.tex.height
        # rix, riy = ax, ay
        glUseProgram(self.program)
        glUniform1i(self.uniforms['tex1'], 0)
        if self.mask == '':
            glUniform1i(self.uniforms['usemask'], 0)
        elif self.mask == 'alpha':
            glUniform1i(self.uniforms['usemask'], -1)
        else:
            rmx, rmy = self.mask.tex_coords[6:8]
            # mx, my = self.mask.width, self.mask.height
            glUniform1i(self.uniforms['usemask'], 1)
            glUniform1i(self.uniforms['mask'], 1)
            glUniform2f(self.uniforms['pixel'], float(rmx)/rix, float(rmy)/riy)
            glUniform2f(self.uniforms['offset'],
                        self.txy[0, 0], self.txy[0, 1])

        glUseProgram(0)

    def set_mask(self, fname):
        self.mask = fname
        if fname:
            if fname == 'alpha':
                self.mask = 'alpha'
            else:
                self.mask = pyglet.image.load(fname).get_texture()
        self.setup_shader()

    def _frmupdate(self, t):
        if (self.clock.time() - self.t0) > 1.0/self.params.fps:
            self.im.set_data('RGB', -self.im.width*3, self.frames.next())
            self.tex = self.im.get_texture()
            self.t0 = self.clock.time()

            if hasattr(self.params, 'series'):
                p = self.params
                for i in xrange(len(p.tile_image_series)):
                    self.txy[i*4:(i+1)*4,
                             :] = p.tile_image_series[i].next().copy()
                    xy = slanttilt(p.tile_disp_series[i].next(
                    ), p.tile_slants[i], p.tile_tilts[i], p.tile_disp_anchors[i])
                    self.xy[i*4:(i+1)*4, :] = xy
                self.vlist._vertices_cache.invalidate()
                self.vlist._tex_coords_cache.invalidate()

    def draw(self):
        self._frmupdate(self.clock.time())
        p = self.params
        # ready to draw
        glPushMatrix()
        glLoadIdentity()
        # glEnable(GL_DEPTH_TEST)
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(-p.slant, 1.0, 0.0, 0.0)
        glRotatef(p.tilt, 0.0, 1.0, 0.0)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.tex.id)
        glUseProgram(self.program)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.tex.id)
        if not isinstance(self.mask, str):
            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, self.mask.id)
        self.vlist.draw(GL_TRIANGLES)
        glUseProgram(0)
        glDisable(GL_TEXTURE_2D)
        # glDisable(GL_DEPTH_TEST)
        glPopMatrix()


class MaskNumpy(stim(width=500.0, height=500.0, sigma=200.0, edge=2.0)):
    """Mask stimulus computed using numpy

    :param sigma: mask radius
    :param edge: power of apperture's Gaussian (slope)
    """

    def __init__(self, pos, params=Params()):
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.pos = pos
        # and (x,y) coordinate for each dot
        self.mask = make_mask(int(p.width), int(p.height), p.sigma, p.edge)

    def draw(self):
        p = self.params
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        self.mask.draw()
        glPopMatrix()


class Mask(stim(width=500.0, height=500.0, bgcolor=(0.0, 0.0, 0.0), sigma=200.0, edge=2.0)):
    """Mask stimulus (GLSL)

    :param sigma: mask radius
    :param edge: power of apperture's Gaussian (slope)
    """
    frag_source = """
        uniform vec3 bgcolor;
        uniform float sigma, edge;
        void main() {
            float x = gl_TexCoord[0].x - 0.5;
            float y = -(gl_TexCoord[0].y - 0.5);
            float m = exp(-0.5*pow(x*x + y*y,edge/2.0)/pow(sigma,edge));
            gl_FragColor.rgba = vec4(bgcolor,1.0-m);
        }
        """

    def __init__(self, pos, params=Params()):
        self.pos = pos
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms = dict(
            map(self.shader.uniform, ['bgcolor', 'sigma', 'edge']))
        glUseProgram(self.program)
        glUniform3f(self.uniforms['bgcolor'], *p.bgcolor)
        glUniform1f(self.uniforms['sigma'], p.sigma)
        glUniform1f(self.uniforms['edge'], p.edge)
        glUseProgram(0)

    def draw(self):
        glUseProgram(self.program)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        w2 = self.params.width/2
        h2 = self.params.height/2
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -h2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -h2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, h2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, h2)
        glEnd()
        glUseProgram(0)
        glPopMatrix()


DotLatticeBase = stim(ap_fs=0.0, ap_sigma=100.0, ap_edge=4.0,
                      gamma=70.0, theta=10.0, dx=40.0, r=1.5,
                      dot_size=150.0, dot_sigma=0.25, dot_fs=0.0,
                      dot_edge=10.0, dot_c=0.4, dot_phi=0.2)


class DotLattice(DotLatticeBase):  # <- specific stimulus
    """Dot-lattice stimulus

    :param ap_fs    : spatial frequency of the mask
    :param ap_sigma : spatial frequency of the mask
    :param ap_edge  : power of apperture's Gaussian (slope)
    :param gamma    : angle
    :param theta    : angle of A nd B directions within lattice
    :param dx       : parameter a, shortest distance
    :param r        : aspect ratio
    :param dot_size : size of dot's texture
    :param dot_sigma: width of dot's Gaussian
    :param dot_fs   : spatial frequency of dot's grating
    :param dot_edge : power of dot's Gaussian (slope)
    :param dot_c    : dot color [0.0,1.0]
    :param dot_ph   : phase of dot's grating
    """

    def __init__(self, pos, params=Params()):
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.pos = pos
        # prepare image of dot of the lattice
        self.dot = make_dot(p.dot_sigma, p.dot_fs,
                            p.dot_phi, p.dot_edge).get_texture()
        # and (x,y) coordinate for each dot
        # "xg" is a helper that return x at known y of Gaussian
        lw = xg(0.01, p.ap_sigma, p.ap_edge)
        # genrate dot center coordintes within the circle of radius lw
        xy = make_lattice(lw, p.dx, p.r, p.gamma, p.theta)

        # to draw thw dots we will use OpenGL DrawArray through pyglet's vertex_list
        N = xy.shape[0]
        self.vlist = pyglet.graphics.vertex_list(N, 'v2d/stream', 'c4f')
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, :] = p.dot_c
        self.colors[:, 3] = 1.0
        # prepare the mask (apperture)
        w = 2*int(1.1*abs(self.xy).max())
        self.mask = make_mask(w, w, p.ap_sigma, p.ap_edge)
        # store the parameter in this class

    def draw(self):
        p = self.params
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(p.gamma, 0.0, 0.0, 1.0)
        glEnable(GL_POINT_SPRITE)
        glEnable(GL_TEXTURE_2D)
        glPointSize(p.dot_size)
        glBindTexture(GL_TEXTURE_2D, self.dot.id)
        self.vlist.draw(pyglet.gl.GL_POINTS)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_POINT_SPRITE)
        # draw the mask (apperture)
        self.mask.draw()
        glPopMatrix()


class Lattice(stim(width=400.0, height=400.0,
                   gamma=70.0, theta=10.0, dx=40.0, r=1.5,
                   dot_size=150.0, dot_sigma=0.25, dot_fs=0.0,
                   dot_edge=10.0, dot_c=0.4, dot_phi=0.2,
                   slant=0.0, tilt=0.0)):
    """Dot-lattice stimulus

    :param width: width of stimulus in pixels
    :param height: height of stimulus in pixels
    :param gamma: angle
    :param theta: angle
    :param dx: parameter a, shortest distance
    :param r: aspect ratio
    :param dot_size: size of dot's texture
    :param dot_sigma: width of dot's Gaussian
    :param dot_fs: spatial frequency of dot's grating
    :param dot_edge: power of dot's Gaussian (slope)
    :param dot_c: dot contrast [0.0,1.0]
    :param dot_ph: phase of dot's grating
    """

    def __init__(self, pos, params=Params()):
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.pos = pos
        # prepare image of dot of the lattice
        self.dot = make_dot(p.dot_sigma, p.dot_fs,
                            p.dot_phi, p.dot_edge).get_texture()
        # and (x,y) coordinate for each dot
        xy = make_lattice(p.width/2.0, p.dx, p.r, p.gamma, p.theta)
        # to draw the dots we will use OpenGL DrawArray through pyglet's vertex_list
        N = xy.shape[0]
        self.vlist = pyglet.graphics.vertex_list(N, 'v2d/stream', 'c4f')
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, :] = 1.0

    def draw(self):
        p = self.params
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glEnable(GL_POINT_SPRITE)
        glEnable(GL_TEXTURE_2D)
        glPointSize(p.dot_size)
        glRotatef(-p.slant, 1.0, 0.0, 0.0)
        glRotatef(p.tilt, 0.0, 1.0, 0.0)
        glBindTexture(GL_TEXTURE_2D, self.dot.id)
        self.vlist.draw(pyglet.gl.GL_POINTS)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_POINT_SPRITE)
        glPopMatrix()


class Pill(stim(th=0.0, R=50.0, d=3.0, alpha=1.0)):
    """Orientation circle stimulus

    :param th   : size of stimulus
    :param R    : radius
    :param d    : width of orientation bar
    """

    def __init__(self, pos, params=Params()):
        self.params = copy_params(self._defaults, params)
        self.pos = pos
        p = self.params
        def ld(t, x, y): return abs(-sin(t)*x+cos(t)*y)
        w2 = int(ceil(p.R*1.2))
        y, x = mgrid[w2:-w2-1:-1, -w2:w2+1]
        apill = (255*g2f(x/p.R, y/p.R, 1.0, 40.0)).astype('u1')
        apill = (apill * (1-exp(-0.5*(ld(p.th, x, y)/p.d)**4.0))).astype('u1')
        h, w = apill.shape
        self.image = pyglet.image.ImageData(w, h, 'L', apill.tostring(), -w)
        self.image.anchor_x = w//2
        self.image.anchor_y = h//2

    def draw(self):
        glColor4f(1.0, 1.0, 1.0, self.params.alpha)
        self.image.blit(self.pos[0], self.pos[1])


class OrientCircle(stim(th=0.0, R=50.0, d=3.0, alpha=1.0)):
    """Orientation circle stimulus

    :param th: size of stimulus
    :param R: radius
    :param d: width of orientation bar
    """
    frag_source = """
    uniform float th, sigma, gap, alpha;
    float edge = 40.0;

    float lined(float t, float x, float y) {
        return abs(-sin(t)*x+cos(t)*y);
    }

    float g(float x, float s2, float e2) {
        return exp(-0.5*pow(abs(x)/s2,e2));
    }

    void main( void ) {
        float x = gl_TexCoord[0].x - 0.5;
        float y = -(gl_TexCoord[0].y - 0.5);
        float c = exp(-0.5*pow(x*x + y*y,edge/2.0)/pow(sigma,edge));
        c = c*(1.0-g(lined(th,x,y),gap,4.0));
        gl_FragColor = vec4( c,c,c,alpha );

    }
    """

    def __init__(self, pos, params=Params()):
        self.pos = pos
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms = dict(
            map(self.shader.uniform, ['th', 'sigma', 'gap', 'alpha']))
        glUseProgram(self.program)
        self.w = p.R*2.5
        glUniform1f(self.uniforms['th'], p.th)
        glUniform1f(self.uniforms['sigma'], 0.4)
        glUniform1f(self.uniforms['gap'], p.d/self.w)
        glUniform1f(self.uniforms['alpha'], p.alpha)
        glUseProgram(0)

    def draw(self):
        p = self.params
        x, y = self.pos
        w2 = self.w/2.0
        glUseProgram(self.program)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)


class Text(stim(msg='Text', size=24)):
    """Text stimulus

    :param msg: string to display
    :params size: font size (default 24)
    """

    def __init__(self, pos, params=Params()):
        self.params = copy_params(self._defaults, params)
        self.pos = pos
        p = self.params
        self.label = text.Label(p.msg,
                                font_name='Times New Roman',
                                font_size=p.size,
                                anchor_x='center',
                                anchor_y='center',
                                x=pos[0], y=pos[1])

    def draw(self):
        glEnable(GL_BLEND)
        glEnable(GL_TEXTURE_2D)
        self.label.draw()


class Dot(stim(c=1.0)):
    """Gaussian dot stimulus

    :param c: contrast [0.0,1.0]
    """

    def __init__(self, pos, params=Params()):
        self.params = copy_params(self._defaults, params)
        im = make_dot(0.17, 0.0, 0.0, 2.0, 64)
        w = im.width
        h = im.height
        im.anchor_x = w//2
        im.anchor_y = h//2
        self.image = im
        self.pos = pos

    def draw(self):
        c = self.params.c
        glColor4f(c, c, c, 1.0)
        self.image.blit(self.pos[0], self.pos[1])


class Dot_Size(stim(c=1.0, sigma=0.17, fs=0.0, phi=0.0, edge=2.0, res=64)):
    """Gaussian dot stimulus with size control

    :param c: contrast [0.0,1.0]
    """

    def __init__(self, pos, params=Params()):
        self.params = copy_params(self._defaults, params)
        sigma = self.params.sigma
        fs = self.params.fs
        phi = self.params.phi
        edge = self.params.edge
        res = self.params.res

        im = make_dot(sigma, fs, phi, edge, res)  # <-type of stimulus
        w = im.width
        h = im.height
        im.anchor_x = w//2
        im.anchor_y = h//2
        self.image = im
        self.pos = pos

    def draw(self):
        c = self.params.c
        glColor4f(c, c, c, 1.0)
        self.image.blit(self.pos[0], self.pos[1])

# ========================================================
# ========================================================
# ========================================================
# ========================================================
# ========================================================


"""
    Above: original untouched functions/classes.
    Below: altered functions/classes that needed to update contrast.
"""

# ========================================================
# ========================================================
# ========================================================
# ========================================================
# ========================================================


def from_Text(path):
    file = open(path, "r")
    content = file.read()
    res2 = list(map(float, content[1:-1].split(',')))
    file.close()
    return res2


"""
    ||$||
"""


def to_Text_Folder(path, response: []):  # saves data to file
    file = open(path, "r")
    content = file.read()
    res2 = list(map(float, content[1:-1].split(',')))
    file.close()
    file = open(path, "w")
    for i in range(len(response)):
        res2.append(response[i])
    file.write(str(res2))
    file.close()


"""
    ||$||
"""


def to_Text(path, response: []):  # allows all other fucntion to access response
    file = open(path, "w")
    file.write(str(response))
    file.close()


"""
    ||$||
"""


def readText_toList(path):  # , path
    file = open(path, "r")
    contents = file.read()
    file.close()
    contents = contents.replace("\t", ",")
     contLists = contents.split('\n')

      ListRows = []
       for j in range(len(contLists)):
            contLists_j = contLists[j].replace("]", "")
            contLists_j = contLists_j.split(",")
            ListRows.append([float(elements) for elements in contLists_j])

        outColumns = [[] for i in range(len(ListRows[0]))]

        for j in range(len(ListRows)):
            for i in range(len(ListRows[0])):
                outColumns[i].append(ListRows[j][i])
        return outColumns


"""
    ||$||
"""


def check_values(value_array):
    new_array = []

    for i in range(len(value_array)):
        if value_array[i] not in new_array:
            new_array.append(value_array[i])
        elif value_array[i] in new_array:
            continue
    return new_array


"""
    ||$||
"""


def findIndex(arrayList, indexNow):
    indexPOSfound = 0
    for i in range(len(arrayList)):
        if int(indexNow) == int(arrayList[i]):
            indexPOSfound = i
            break
        elif int(indexNow) != int(arrayList[i]):
            pass
    return indexPOSfound


"""
    ||$||
"""


def findIndexFloat(arrayList, indexNow):
    indexPOSfound = 0
    for i in range(len(arrayList)):
        if (indexNow) == (arrayList[i]):
            indexPOSfound = i
            break
        elif (indexNow) != (arrayList[i]):
            pass
    return indexPOSfound


"""
    ||$||
"""


def count_values_type(list_of_values, value_array, startIndex):
    count_type_array = []
    total = 0
    for z in range(len(value_array)):
        count = 0.0
        for i in range(startIndex, len(list_of_values), 1):
            if list_of_values[i] == value_array[z]:
                count += 1
            elif list_of_values[i] != value_array[z]:
                continue
        count_type_array.append([value_array[z], count])
    for index in range(len(count_type_array)):
        total += count_type_array[index][1]
    return count_type_array, total


"""
    ||$||
"""


def count_Abs_type(count_type_array):
    checkedValues = []
    checkekCounts = []
    for i in range(len(count_type_array)):
        if abs(count_type_array[i][0]) not in checkedValues:
            checkedValues.append(abs(count_type_array[i][0]))
            checkekCounts.append(count_type_array[i][1])
        elif abs(count_type_array[i][0]) in checkedValues:
            indexfound = findIndexFloat(
                checkedValues, abs(count_type_array[i][0]))
            checkekCounts[indexfound] = checkekCounts[indexfound] + \
                count_type_array[i][1]

    returnType = []
    for i in range(len(checkedValues)):
        e1 = checkedValues[i]
        e2 = checkekCounts[i]
        returnType.append([e1, e2])
    return returnType


"""
    ||$||
"""


def returnOnce(lisT):
    newList = []
    for i in range(len(lisT)):
        value = abs(lisT[i])
        if value not in newList:
            newList.append(value)
        elif value in newList:
            continue
    return newList


"""
    ||$||
"""


def appendTrials(trails):
    arrayT = []
    for i in range(0, len(trails), 1):
        arrayT.append(trails[i][0])
    return arrayT


"""
    ||$||
"""


def convertToArcangle(distanceM, distanceToMonitor):
    value = np.arctan(2*distanceM/distanceToMonitor)
    return value/(arcAngle_to_radians*2)


"""
    ||$||
"""

# ========================================================
# ========================================================
# ========================================================
# ========================================================
# ========================================================


class Line_staircase_LR_ADMs(stim(length=100.0, width=10.0, angle=0.0, color=(1.0, 1.0, 1.0, 1.0))):
    def __init__(self, fileParams, filesDataMain, admTEXT, bkg, fixation_crt,
                 pos, posCentre, params=Params(), params0=Params()):  # , params1=Params()):
        self.pos = pos
        self.fileParams = fileParams
        self.filesDataMain = filesDataMain
        self.fixation_crt = fixation_crt
        self.bkg = bkg
        self.admTEXT = admTEXT

        self.params = copy_params(self._defaults, params)
        self.params0 = copy_params(self._defaults, params0)
        sigma0 = self.params0.sigma
        fs0 = self.params0.fs
        phi0 = self.params0.phi
        edge0 = self.params0.edge
        res0 = self.params0.res

        im0 = make_dot(sigma0, fs0, phi0, edge0, res0)
        w = im0.width
        h = im0.height
        im0.anchor_x = w//2
        im0.anchor_y = h//2

        self.image0 = im0
        self.posCentre = posCentre

    def draw(self):
        import Functions.functionUSE as funcs
        c2 = self.fixation_crt
        glColor4f(c2, c2, c2, 1.0)
        self.image0.blit(self.posCentre[0], self.posCentre[1])

        cL = funcs.adMethod_luminance(
            self.posCentre, self.pos, self.admTEXT, self.fileParams, self.filesDataMain)
        # === ... ===

        self.params.color = (cL, cL, cL, 1.0)
        # params.color):
        if hasattr(self.params, 'color') and not iterable(self.params.color):
            self.params.color = [self.params.color]*3
        self.params = copy_params(self._defaults, self.params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy                  = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.length, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.params.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()


class Line_two_LR_ADMs(stim(length=100.0, width=10.0, angle=0.0, color=(1.0, 1.0, 1.0, 1.0))):
    def __init__(self, fileParams, bkg, fixation_crt,
                 pos, pos1, posCentre, params=Params(), params1=Params(), params2=Params(), params0=Params()):  # , params1=Params()):
        self.pos = pos
        self.pos1 = pos1
        self.fileParams = fileParams
        self.fixation_crt = fixation_crt
        self.bkg = bkg

        self.params = copy_params(self._defaults, params)

        self.params1 = copy_params(self._defaults, params1)
        length = self.params1.length
        width = self.params1.width
        angle = self.params1.angle
        color = self.params1.color

        self.params2 = copy_params(self._defaults, params2)
        angle2 = self.params2.angle
        color2 = self.params2.color

        self.params0 = copy_params(self._defaults, params0)

        sigma0 = self.params0.sigma
        fs0 = self.params0.fs
        phi0 = self.params0.phi
        edge0 = self.params0.edge
        res0 = self.params0.res

        im0 = make_dot(sigma0, fs0, phi0, edge0, res0)
        w = im0.width
        h = im0.height
        im0.anchor_x = w//2
        im0.anchor_y = h//2

        self.image0 = im0
        self.posCentre = posCentre

        cL = from_Text(self.fileParams)[0]
        self.params.color = (cL, cL, cL, 1.0)
        self.params1.color = (cL, cL, cL, 1.0)

        # ============= line 1 ===============
        # params.color):
        if hasattr(self.params, 'color') and not iterable(self.params.color):
            self.params.color = [self.params.color]*3
        # self.params = copy_params(self._defaults,self.params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy  = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.length, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()
        # ============= line 2 ===============
        # params.color):
        if hasattr(self.params1, 'color') and not iterable(self.params1.color):
            self.params1.color = [self.params1.color]*3
        # self.params1 = copy_params(self._defaults,self.params1)
        p1 = self.params1
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy          = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist1 = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist1.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p1.length, p1.width]
        self.colors = from_ctypes(self.vlist1.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p1.color)] = p1.color
        self.vlist1._vertices_cache.invalidate()
        self.vlist1._colors_cache.invalidate()
        self.params2.color = (cL, cL, cL, 1.0)
        # ============= line 3 ===============
        # params.color):
        if hasattr(self.params2, 'color') and not iterable(self.params2.color):
            self.params2.color = [self.params2.color]*3
        # self.params2 = copy_params(self._defaults,self.params2)
        p2 = self.params2
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy  = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist2 = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist2.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p2.length, p2.width]
        self.colors = from_ctypes(self.vlist2.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p2.color)] = p2.color
        self.vlist2._vertices_cache.invalidate()
        self.vlist2._colors_cache.invalidate()

    def draw(self):
        c2 = self.fixation_crt
        glColor4f(c2, c2, c2, 1.0)
        self.image0.blit(self.posCentre[0], self.pos[1])

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.posCentre[0], self.posCentre[1], 0.0)
        glRotatef(self.params2.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist2.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.params.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos1[0], self.pos1[1], 0.0)
        glRotatef(self.params1.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist1.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()


"""
    ================================= ||$|| =================================
"""


class Sound_Line(stim(wavefile=None)):
    """Sound stimulus
    
    :param wavefile: filename of sound file to be played
    """

    def __init__(self, posCentre, pos, params=Params(), params0=Params(), params1=Params()):
        sound_cache = {}
        self.pos = pos
        self.params = copy_params(self._defaults, params)
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # load pyglet sound object
        if self.params.wavefile not in sound_cache:
            sound_cache[self.params.wavefile] = pyglet.media.load(
                self.params.wavefile)
        self.sound = sound_cache[self.params.wavefile]
        self.played = False

        self.params0 = copy_params(self._defaults, params0)
        sigma = self.params0.sigma
        fs = self.params0.fs
        phi = self.params0.phi
        edge = self.params0.edge
        res = self.params0.res

        im = make_dot(sigma, fs, phi, edge, res)  # <-type of stimulus
        w = im.width
        h = im.height
        im.anchor_x = w//2
        im.anchor_y = h//2
        self.image = im
        self.posCentre = posCentre

        self.pos = pos

        if hasattr(params1, 'color') and not iterable(params1.color):
            params1.color = [params1.color]*3
        self.params1 = copy_params(self._defaults, params1)
        p = self.params1
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.length, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

    def draw(self):
        p = self.params
        # play sound
        if not self.played:
            self.sound.play()
            self.played = True

        c = self.params0.c
        glColor4f(c, c, c, 1.0)
        self.image.blit(self.posCentre[0], self.posCentre[1])

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.params1.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()


# =====================================================================================
# =====================================================================================
# =====================================================================================

class RDK(stim(width=200.0, n0=500, n1=500, d0=[0.0, 1.0], d1=[0.3, -1.0],
               theta=0.0, tilt=0.0, slant=0.0)):
    """Random Dot Kinematogram

    Stimulus consists of two groups of dots. Dots within groups
    move together, motion of each group can be controlled independently.
    
    :param width: width and height in pixels
    :param n0: number of dots in group 1
    :param n1: number of dots in group 2
    :param d0: X,Y speed of group 1 (xy[t+1] = xy[t] + d0)
    :param d1: X,Y speed of group 2 (xy[t+1] = xy[t] + d0)
    :param theta: rotation in screen plane
    :param tilt: tilt angle
    :param slant: slant angle
    """

    def __init__(self, pos, params=Params()):
        self.pos = pos
        self.batch = pyglet.graphics.Batch()
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        N = p.n0 + p.n1
        self.dot = make_dot(0.25, 0.0, 0.0, 4.0).get_texture()
        self.vlist = self.batch.add(N, GL_POINTS, None, 'v3d', 'c4f/stream')
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 3))
        self.xy0 = self.xy[:p.n0, :2]   # Group0 xy coordinates
        self.xy1 = self.xy[p.n0:, :2]   # Group1 xy coordinates
        self.xy0[...] = rand(p.n0, 2)*r_[p.width, p.width]
        self.xy1[...] = rand(p.n1, 2)*r_[p.width, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[...] = 1.0
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

    def draw(self):
        p = self.params
        t = self.clock.time()-self.t0
        self.xy0[...] = (self.xy0 + array(p.d0)) % p.width
        self.xy1[...] = (self.xy1 + array(p.d1)) % p.width
        self.vlist._vertices_cache.invalidate()
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0]-p.width/2.0, self.pos[1]-p.width/2.0, 0.0)
        glRotatef(-p.slant, 1.0, 0.0, 0.0)
        glRotatef(p.tilt, 0.0, 1.0, 0.0)
        glRotatef(p.theta, 0.0, 0.0, 1.0)
        glEnable(GL_POINT_SPRITE)
        glEnable(GL_TEXTURE_2D)
        glPointSize(10.0)
        glBindTexture(GL_TEXTURE_2D, self.dot.id)
        self.vlist.draw(pyglet.gl.GL_POINTS)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_POINT_SPRITE)
        glPopMatrix()


class RDKMod(stim(width=200.0, n=500, theta=0.0, a=1.0, b=1.0,
                  f=0.0, phi=0.0, noise=0.0, life=500.0, gamma=0.0,
                  tilt=0.0, slant=0.0)):
    """Random Dot Kinematogram with modulated speed

    Dots move together along axis controlled by "theta" parameter.
    Speed of each dot is controlled by

      vx = a + b*cos(2*pi*f*cos(gamma)*x[0] + phi)
      vy = a + b*cos(2*pi*f*sin(gamma)*y[0] + phi)

    The speed is computed from the initial location (x[0],y[0]) 
    of each dot. Then
       
      R = rand-0.5
      x[t+1] = x[t] + vx + vx*noise*R
      y[t+1] = y[t] + vy + vy*noise*R
    
    :param width: width and height in pixels
    :param n: number of dots
    :param theta: motion direction in radians
    :param gamma: angle of modulation relative to the motion direction in radians
    :param a: speed modulation parameter a
    :param b: speed modulation parameter b
    :param f: speed modulation parameter f
    :param phi: speed modulation parameter phi
    :param tilt: tilt angle
    :param slant: slant angle
    """

    def __init__(self, pos, params=Params()):
        self.pos = pos
        self.batch = pyglet.graphics.Batch()
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        N = p.n
        self.dot = make_dot(0.25, 0.0, 0.0, 4.0).get_texture()
        self.vlist = self.batch.add(N, GL_POINTS, None, 'v3d', 'c4f/stream')
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 3))
        self.xy0 = self.xy[:, :2]   # Group0 xy coordinates
        self.xy0[...] = rand(p.n, 2)
        # v = p.a + p.b*cos(2*pi*p.f*self.xy0[:,1] + p.phi)
        rx = cos(p.gamma)*self.xy0[:, 0] + sin(p.gamma)*self.xy0[:, 1]
        v = p.a + p.b*cos(2*pi*p.f*rx + p.phi)
        self.xy0 *= r_[p.width, p.width]
        self.speed = [1.0, 0.0]*v.reshape(-1, 1)
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[...] = 1.0
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()
        self.draw = self.draw0

    def draw0(self):
        self.life = self.clock.time() + self.params.life/1000.0*rand(self.params.n)
        self.draw = self.draw1

    def draw1(self):
        p = self.params
        i = self.clock.time() - self.life > p.life/1000.0
        # m = lambda x: x//1.0 + arcsin(2*(x%1.0)-1.0)/pi+0.5
        # xx = linspace(0,1,100)
        # a = linspace(-1,1,200)
        # hist((m(2*rand(500)-0.75)+m(0.75))/2.0,51,normed=True)
        # plot(xx,sin(2*pi*2.0*xx-0.75*pi/2)+1)
        newxy = rand(i.sum(), 2)
        # v = p.a + p.b*cos(2*pi*p.f*newxy[:,1] + p.phi)
        rx = cos(p.gamma)*newxy[:, 0] + sin(p.gamma)*newxy[:, 1]
        v = p.a + p.b*cos(2*pi*p.f*rx + p.phi)
        self.xy0[i, :] = r_[p.width, p.width]*newxy
        self.speed[i, :] = [1.0, 0.0]*v.reshape(-1, 1)
        self.life[i, :] = self.clock.time() + self.params.life / \
            1000.0*rand(i.sum())
        vn = p.noise*(rand(p.n)-0.5)
        self.xy0[...] = (self.xy0 + self.speed + self.speed *
                         vn.reshape(-1, 1)) % p.width
        self.vlist._vertices_cache.invalidate()
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(180.0*p.theta/pi, 0.0, 0.0, 1.0)
        glRotatef(-p.slant, 1.0, 0.0, 0.0)
        glRotatef(p.tilt, 0.0, 1.0, 0.0)
        glTranslatef(-p.width/2.0, -p.width/2.0, 0.0)
        glEnable(GL_POINT_SPRITE)
        glEnable(GL_TEXTURE_2D)
        glPointSize(10.0)
        glBindTexture(GL_TEXTURE_2D, self.dot.id)
        self.vlist.draw(pyglet.gl.GL_POINTS)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_POINT_SPRITE)
        glPopMatrix()


class Rectangle(stim(width=100.0, height=100.0, angle=0.0, linewidth=1.0,
                     facecolor=(1.0, 1.0, 1.0, 1.0), edgecolor=[])):
    def __init__(self, pos, params=Params()):
        from itertools import cycle
        self.pos = pos
        if hasattr(params, 'facecolor') and not iterable(params.facecolor):
            params.facecolor = [params.facecolor]*3
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.width, p.height]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.facecolor)] = p.facecolor
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()
        # outline
        self.edgelist = pyglet.graphics.vertex_list(4, 'v2d/stream', 'c4f')
        self.edgexy = from_ctypes(self.edgelist.vertices, 'f8', (N, 2))
        self.edgexy[...] = self.xy
        self.edgecolors = from_ctypes(self.edgelist.colors, 'f4', (N, 4))
        self.edgecolors[:, 3] = 1.0
        self.edgecolors[:, :len(p.edgecolor)] = p.edgecolor
        self.edgelist._vertices_cache.invalidate()
        self.edgelist._colors_cache.invalidate()
        #
        if not iterable(p.angle):
            p.angle = [p.angle]
        self.angle = cycle(p.angle)

    def draw(self):
        p = self.params
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(next(self.angle), 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        if p.facecolor:
            self.vlist.draw(GL_TRIANGLES)
        if p.edgecolor:
            glLineWidth(p.linewidth)
            self.edgelist.draw(GL_LINE_LOOP)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()


class Cube(stim(width=100.0, height=100.0, depth=100.0, angles=0.0, linewidth=1.0,
                facecolor=(1.0, 1.0, 1.0, 1.0), edgecolor=[])):
    def __init__(self, pos, params=Params()):
        from itertools import cycle
        self.pos = pos
        if hasattr(params, 'facecolor') and not iterable(params.facecolor):
            params.facecolor = [params.facecolor]*3
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3,
                     1, 5, 6, 1, 6, 2,
                     5, 4, 7, 5, 7, 6,
                     4, 0, 3, 4, 3, 7,
                     0, 1, 5, 0, 5, 4,
                     3, 2, 6, 3, 6, 7])
        xy = r_[0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0,0.0,
                0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0,1.0].reshape(-1,3) - 0.5
        N = xy.shape[0]
        self.vlist = pyglet.graphics.vertex_list_indexed(
            N, ind, 'v3d/stream', 'c4f')
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 3))
        self.xy[...] = xy * r_[p.width, p.height, p.depth]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.facecolor)] = p.facecolor
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()
        # outline
        indw = array([0, 1, 1, 2, 2, 3, 3, 0,
                      1, 5, 5, 6, 6, 2, 2, 1,
                      5, 4, 4, 7, 7, 6, 6, 5,
                      4, 0, 0, 3, 3, 7, 7, 4,
                      0, 1, 1, 5, 5, 4, 4, 0,
                      3, 2, 2, 6, 6, 7, 7, 3])
        self.edgelist = pyglet.graphics.vertex_list_indexed(
            N, indw, 'v3d/stream', 'c4f')
        self.edgexy = from_ctypes(self.edgelist.vertices, 'f8', (N, 3))
        self.edgexy[...] = self.xy
        self.edgecolors = from_ctypes(self.edgelist.colors, 'f4', (N, 4))
        self.edgecolors[:, 3] = 1.0
        self.edgecolors[:, :len(p.edgecolor)] = p.edgecolor
        self.edgelist._vertices_cache.invalidate()
        self.edgelist._colors_cache.invalidate()
        #
        if not iterable(p.angle):
            p.angle = [p.angle]
        self.angle = cycle(p.angle)

    def draw(self):
        p = self.params
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.angle.next(), 0.0, 1.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        if p.facecolor:
            self.vlist.draw(GL_TRIANGLES)
        if p.edgecolor:
            glLineWidth(p.linewidth)
            self.edgelist.draw(GL_LINES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()

# import functionUSE as funcs


class RectangleBitDepth(stim(width=100.0, height=100.0, angle=0.0, linewidth=1.0,
                             facecolor=(1.0, 1.0, 1.0, 1.0), edgecolor=[])):
    def __init__(self, pos, pos1, bkg_CPU, fileParams,
                 params=Params(), params1=Params(), params2=Params()):

        self.params1 = copy_params(self._defaults, params1)
        self.params2 = copy_params(self._defaults, params2)
        self.pos1 = pos1
        self.p1 = self.params1
        self.p2 = self.params2
        self.fileParams = fileParams
        self.pos = pos
        self.bkg_CPU = bkg_CPU
        self.params = copy_params(self._defaults, params)

    def draw(self):
        from itertools import cycle
        import Functions.functionUSE as funcs

        max_cpu, minLum = 1.0, 0.0
        rateLog = 0.95

        listOutMain = from_Text(self.fileParams)
        contrast_cpu = listOutMain[0]
        rDWUP = listOutMain[1]
        printSTR = rDWUP*np.log10(rateLog)
        # rDWUP           = funcs.get_bitdepth_rDW(self.fileParams)
        # =====================================================================

        if listOutMain[2] == 1:
            rDW = rDWUP*np.log10(rateLog)
        elif listOutMain[2] == 0:
            rDW = 0

        base_cL = (contrast_cpu-self.bkg_CPU)/(max_cpu-self.bkg_CPU)
        cL_param_new = base_cL*pow(10, rDW)  # base_cL*0.5
        weberCRT = cL_param_new
        cpu_LUM = ((max_cpu-self.bkg_CPU)*weberCRT)+self.bkg_CPU
        cL_param_new = contrast_cpu+0.02*rDW  # cpu_LUM
        # =====================================================================

        listOutMain[0] = cL_param_new
        listOutMain[2] = 0
        to_Text(self.fileParams, listOutMain)
        cL = cL_param_new

        self.p1.msg = 'cpu: '+str(cL) + ' rateDW:'+str(round(printSTR, 5))
        self.label = text.Label(self.p1.msg,
                                font_name='Times New Roman',
                                font_size=self.p1.size,
                                anchor_x='center',
                                anchor_y='center',
                                x=self.pos[0], y=self.pos1[1]-50)

        self.p2.msg = 'Weber C: '+str(weberCRT)
        self.label0 = text.Label(self.p2.msg,
                                 font_name='Times New Roman',
                                 font_size=self.p1.size,
                                 anchor_x='center',
                                 anchor_y='center',
                                 x=self.pos1[0], y=self.pos1[1]-50)

        params = self.params
        params.facecolor = (cL, cL, cL, 1.0)

        if hasattr(params, 'facecolor') and not iterable(params.facecolor):
            params.facecolor = [params.facecolor]*3
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.width, p.height]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.facecolor)] = p.facecolor
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()
        # outline
        self.edgelist = pyglet.graphics.vertex_list(4, 'v2d/stream', 'c4f')
        self.edgexy = from_ctypes(self.edgelist.vertices, 'f8', (N, 2))
        self.edgexy[...] = self.xy
        self.edgecolors = from_ctypes(self.edgelist.colors, 'f4', (N, 4))
        self.edgecolors[:, 3] = 1.0
        self.edgecolors[:, :len(p.edgecolor)] = p.edgecolor
        self.edgelist._vertices_cache.invalidate()
        self.edgelist._colors_cache.invalidate()
        #
        if not iterable(p.angle):
            p.angle = [p.angle]
        self.angle = cycle(p.angle)

        p = self.params
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(next(self.angle), 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        if p.facecolor:
            self.vlist.draw(GL_TRIANGLES)
        if p.edgecolor:
            glLineWidth(p.linewidth)
            self.edgelist.draw(GL_LINE_LOOP)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()

        # add text cpu luminance ====
        glEnable(GL_BLEND)
        glEnable(GL_TEXTURE_2D)
        self.label.draw()
        self.label0.draw()


class FileSave():
    """File save stimulus conditions

    """

    def __init__(self, pos, fileParamsMain, filename_params, path_main, admTEXT, nUP, params=Params()):
        self.pos = pos
        self.fileParamsMain = fileParamsMain
        self.filename_params = filename_params
        self.admTEXT = admTEXT
        self.nUP = nUP

        dataParamsMain = from_Text(self.fileParamsMain)
        dataParams = from_Text(self.filename_params)
        outText = self.admTEXT
        nUP = self.nUP

        if np.round((self.pos[1])*pixel_metre_ratio, 4) >= 0:
            value_Response = 0
            stringResponse = 'UP: '
        elif np.round((self.pos[1])*pixel_metre_ratio, 4) < 0:
            value_Response = 1
            stringResponse = 'DOWN: '

        print('Probe:', value_Response, ':', stringResponse,
              np.round((self.pos[1])*pixel_metre_ratio, 4))

        dataParams[5] = nUP
        dataParams[11] = np.round(
            (self.pos[1])*pixel_metre_ratio, 4)  # <-- y-axis
        dataParams[3] = np.round(
            (self.pos[0])*pixel_metre_ratio, 4)  # <-- x-axis
        dataParams[1] = value_Response
        dataParamsMain[0] = outText

        to_Text(self.filename_params,    dataParams)
        to_Text(self.fileParamsMain, dataParamsMain)

    def draw(self):
        pass


class Line_ADM(stim(length=100.0, width=10.0, angle=0.0, color=(1.0, 1.0, 1.0, 1.0))):
    def __init__(self, posCentre, pos, admTEXT, fileParams, filesDataMain, params=Params()):

        self.posCentre = posCentre
        self.pos = pos
        self.admTEXT = admTEXT
        self.fileParams = fileParams
        self.filesDataMain = filesDataMain
        self.params = copy_params(self._defaults, params)

    def draw(self):
        import Functions.functionUSE as funcs
        params = self.params
        cL = funcs.adMethod_luminance(
            self.posCentre, self.pos,  self.admTEXT, self.fileParams, self.filesDataMain)
        params.color = (cL, cL, cL, 1.0)

        if hasattr(params, 'color') and not iterable(params.color):
            params.color = [params.color]*3
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.length, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.params.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()


class Line_ADM_Termination(stim(length=100.0, width=10.0, angle=0.0, color=(1.0, 1.0, 1.0, 1.0))):
    def __init__(self, posCentre, pos, admTEXT, fileParamsMain, fileParams, fileParamsPosition, filesDataMain, params=Params()):
        self.pos = pos
        self.posCentre = posCentre
        self.NAN = admTEXT
        self.fileParams = fileParams
        self.filesDataMain = filesDataMain
        self.params = copy_params(self._defaults, params)
        self.filePosition = fileParamsPosition
        self.fileParamsMain = fileParamsMain

    def draw(self):
        import Functions.functionUSE as funcs
        self.dataPosition = from_Text(self.filePosition)
        self.px = self.dataPosition[0]+self.posCentre[0]
        self.py = self.pos[1]
        dataParamsMain = from_Text(self.fileParamsMain)
        # admTEXT # <- needs to be accesed just liek position.
        admTEXT = dataParamsMain[0]

        params = self.params
        cL = funcs.adMethod_luminance_ID(
            admTEXT, self.fileParams, self.filesDataMain)
        params.color = (cL, cL, cL, 1.0)
        self.pos = [self.px, self.py]
        """
        Then save to a file for posX and posY only, which can be accesed by "ADM trial".
        """
        if hasattr(params, 'color') and not iterable(params.color):
            params.color = [params.color]*3
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.length, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.params.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()


class Line_ADM_Flicker(stim(length=100.0, width=10.0, angle=0.0, color=(1.0, 1.0, 1.0, 1.0))):
    def __init__(self, posCentre, pos, admTEXT, fileParamsMain, fileParams, fileParamsPosition, filesDataMain, params=Params()):
        self.pos = pos
        self.posCentre = posCentre
        self.NAN = admTEXT
        self.fileParams = fileParams
        self.filesDataMain = filesDataMain
        self.params = copy_params(self._defaults, params)
        self.filePosition = fileParamsPosition
        self.fileParamsMain = fileParamsMain

    def draw(self):
        import Functions.functionUSE as funcs
        self.px = self.pos[0]
        self.py = self.pos[1]
        dataParamsMain = from_Text(self.fileParamsMain)
        # admTEXT # <- needs to be accesed just liek position.
        admTEXT = dataParamsMain[0]

        params = self.params
        cL = funcs.adMethod_luminance_ID(
            admTEXT, self.fileParams, self.filesDataMain)
        params.color = (cL, cL, cL, 1.0)
        self.pos = [self.px, self.py]
        """
        Then save to a file for posX and posY only, which can be accesed by "ADM trial".
        """
        if hasattr(params, 'color') and not iterable(params.color):
            params.color = [params.color]*3
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.length, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.params.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()


class Grating_M(stim(width=200.0, fs=10.0, ph=0.0, speed=0.0, contr=1.0, theta=0.0, bg=0.5,
                     box=False, Lbg=24.65, Lmin=0.0, Lmax=49.3, gamma=2.5, BTRR=63.2)):
    """Grating stimulus
    
    :param width: size of stimulus in pixels
    :param fs: spatial frequncy
    :param ph: phase
    :param speed: speed
    :param contr: contrast  
    """
    frag_source = """
        //precision highp float;
        
        uniform float fs;
        uniform float phase;
        uniform float contr;
        uniform float bg;
        uniform float box;
        uniform float theta;
        uniform float Lbg, Lmin, Lmax, gamma, BTRR;
        
        vec3 lum2image(float c) {
            vec3 vout;
            float U = 255.0*pow(((1+c)*Lbg-Lmin)/(Lmax-Lmin),1.0/gamma);
            float b1 = (BTRR+1.0)/BTRR;
            //float b = min(floor(U*b1),255.0);
            float b = min(floor(U*b1),255.0) + 1.0/32.0;
            //float b2 = floor((U-b/b1)*(BTRR+1.0));
            float b2 = floor((U-b/b1)*(BTRR+1.0)) + 1.0/32.0;
            vout = vec3(b2/255.0, 0.0 ,b/255.0);
            return vout;
        }

        void main() {
            float x = gl_TexCoord[0].x - 0.5;
            float y = -(gl_TexCoord[0].y - 0.5);
            float m = 1;
            
            // float m = abs(sin(fs*x)+ phase); 
            //float m = exp(-0.5*(x*x + y*y)/pow(0.17,2.0));
            //float c = m*contr*cos(fs*x + phase);

            float c = m*contr*sin(fs*(x*cos(theta)+y*sin(theta)) + phase);
            if (box == 1.0) {
                gl_FragColor.rgba = vec4(lum2image(c),1.0);
            } else {
                c = bg + c/2.0;
                gl_FragColor.rgba = vec4(c,c,c,1.0);
            }
        }
        """
    # m = exp(-0.5*(x*x + y*y)/pow(0.17,2.0));
    # abs(sin(fs*x))

    def __init__(self, pos, params=Params()):
        self.pos = pos
        self.params = copy_params(self._defaults, params)
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms = dict(map(self.shader.uniform,
                                 ['fs', 'phase', 'contr', 'theta', 'bg', 'box', 'Lbg',
                                  'Lmin', 'Lmax', 'gamma', 'BTRR']))

        # self.params.contr = 100

        glUseProgram(self.program)
        glUniform1f(self.uniforms['phase'], 0.0)
        glUniform1f(self.uniforms['fs'], self.params.fs)
        glUniform1f(self.uniforms['contr'], self.params.contr)
        glUniform1f(self.uniforms['theta'], self.params.theta)
        glUniform1f(self.uniforms['bg'], self.params.bg)
        glUniform1f(self.uniforms['box'], self.params.box)
        glUniform1f(self.uniforms['Lbg'], self.params.Lbg)
        glUniform1f(self.uniforms['Lmin'], self.params.Lmin)
        glUniform1f(self.uniforms['Lmax'], self.params.Lmax)
        glUniform1f(self.uniforms['gamma'], self.params.gamma)
        glUniform1f(self.uniforms['BTRR'], self.params.BTRR)
        glUseProgram(0)

    def draw(self):
        p = self.params
        x, y = self.pos
        w2 = p.width/2.0
        glUseProgram(self.program)
        ph = p.speed*(self.clock.time()-self.t0)
        glUniform1f(self.uniforms['phase'], ph)

        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)

# ========

class Grating_Mnew(stim(width=200.0, fs=10.0, ph=0.0, speed=0.0, contr=1.0, theta=0.0, bg=0.5,
                   box=False, Lbg=24.65, Lmin=0.0, Lmax=49.3, gamma=2.5, BTRR=63.2)):
    """Grating stimulus
    
    :param width: size of stimulus in pixels
    :param fs: spatial frequncy
    :param ph: phase
    :param speed: speed
    :param contr: contrast  
    """
    frag_source = """
        //precision highp float;
        
        uniform float fs;
        uniform float phase;
        uniform float contr;
        uniform float bg;
        uniform float box;
        uniform float theta;
        uniform float Lbg, Lmin, Lmax, gamma, BTRR;
        
        vec3 lum2image(float c) {
            vec3 vout;
            float U = 255.0*pow(((1+c)*Lbg-Lmin)/(Lmax-Lmin),1.0/gamma);
            float b1 = (BTRR+1.0)/BTRR;
            //float b = min(floor(U*b1),255.0);
            float b = min(floor(U*b1),255.0) + 1.0/32.0;
            //float b2 = floor((U-b/b1)*(BTRR+1.0));
            float b2 = floor((U-b/b1)*(BTRR+1.0)) + 1.0/32.0;
            vout = vec3(b2/255.0, 0.0 ,b/255.0);
            return vout;
        }

        void main() {
            float x = gl_TexCoord[0].x - 0.5;
            float y = -(gl_TexCoord[0].y - 0.5);
            float m;
            
            m = exp(-0.5*((x*x)/pow(100,2) + (y*y)/pow(0.02,2))); // <- 2 or 2.5
    
            //float m = abs(sin(fs*x)+ phase); 
            //float m = exp(-0.5*(x*x + y*y)/pow(0.17,2.0));
            //float c = m*contr*cos(fs*x + phase);
            
            float peakNew;
            float peak = sin(fs*(x*cos(theta)+y*sin(theta)) + phase);
            if (peak >= 0.9 && peak < 0.99){
                peakNew = 1.0;
            } else if (peak >= 0.99 && peak <= 1.0){
                peakNew = -1.0;
            } else {
                peakNew = 0.0;
            }
            float c = m*contr*peakNew;
            if (box == 1.0) {
                gl_FragColor.rgba = vec4(lum2image(c),1.0);
            } else {
                c = bg + c/2.0;
                gl_FragColor.rgba = vec4(c,c,c,1.0);
            }
        }
        """
    # m = exp(-0.5*(x*x + y*y)/pow(0.17,2.0));
    # abs(sin(fs*x))

    def __init__(self, pos, params=Params()):
        self.pos = pos
        self.params = copy_params(self._defaults, params)
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms = dict(map(self.shader.uniform,
                                 ['fs', 'phase', 'contr', 'theta', 'bg', 'box', 'Lbg',
                                  'Lmin', 'Lmax', 'gamma', 'BTRR']))

        # self.params.contr = 100

        glUseProgram(self.program)
        glUniform1f(self.uniforms['phase'], 0.0)  # was 0.0
        glUniform1f(self.uniforms['fs'], self.params.fs)
        glUniform1f(self.uniforms['contr'], self.params.contr)
        glUniform1f(self.uniforms['theta'], self.params.theta)
        glUniform1f(self.uniforms['bg'], self.params.bg)
        glUniform1f(self.uniforms['box'], self.params.box)
        glUniform1f(self.uniforms['Lbg'], self.params.Lbg)
        glUniform1f(self.uniforms['Lmin'], self.params.Lmin)
        glUniform1f(self.uniforms['Lmax'], self.params.Lmax)
        glUniform1f(self.uniforms['gamma'], self.params.gamma)
        glUniform1f(self.uniforms['BTRR'], self.params.BTRR)
        glUseProgram(0)

    def draw(self):
        p = self.params
        x, y = self.pos
        w2 = p.width/2.0
        glUseProgram(self.program)
        ph = p.speed*(self.clock.time()-self.t0)
        glUniform1f(self.uniforms['phase'], ph)

        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)


# =========
class Grating_ADM(stim(width=200.0, fs=10.0, ph=0.0, speed=0.0, contr=1.0, theta=0.0, bg=0.5,
                       box=False, Lbg=24.65, Lmin=0.0, Lmax=49.3, gamma=2.5, BTRR=63.2, SdeX=0.05, SdeY=0.05)):
    """Grating stimulus
    
    :param width: size of stimulus in pixels
    :param fs: spatial frequncy
    :param ph: phase
    :param speed: speed
    :param contr: contrast  
    """
    frag_source = """
        //precision highp float;
        
        uniform float fs;
        uniform float phase;
        uniform float contr;
        uniform float bg;
        uniform float box;
        uniform float theta;
        uniform float Lbg, Lmin, Lmax, gamma, BTRR;
        uniform float width;  // Declare width uniform  # <- added
        uniform float SdeX;
        uniform float SdeY;
        
        vec3 lum2image(float c) {
            vec3 vout;
            float U = 255.0*pow(((1+c)*Lbg-Lmin)/(Lmax-Lmin),1.0/gamma);
            float b1 = (BTRR+1.0)/BTRR;
            //float b = min(floor(U*b1),255.0);
            float b = min(floor(U*b1),255.0) + 1.0/32.0;
            //float b2 = floor((U-b/b1)*(BTRR+1.0));
            float b2 = floor((U-b/b1)*(BTRR+1.0)) + 1.0/32.0;
            vout = vec3(b2/255.0, 0.0 ,b/255.0);
            return vout;
        }

        void main() {
            float x = gl_TexCoord[0].x - 0.5;
            float y = -(gl_TexCoord[0].y - 0.5);
            float pi = 2.0 * acos(0.0);
            float Sde = 0.03; // 0.05 or 0.17 | USE: Sde = 0.03, 0.025 for <10cdm2
            //float m = exp(-0.5*(x*x + y*y)/pow(Sde,2)); // <- 2 or 2.5
            float m = exp(-0.5*((x*x)/pow(SdeX,2) + (y*y)/pow(SdeY,2)));
            
            //float m = (1.0/(2.0*pi*pow(Sde,2.0)))*exp(-(pow(x,2.0)+pow(y,2.0))/(2.0*pow(Sde,2.0))); 
            //float m = abs(sin(fs*x)+phase);
            //float c = m*contr*cos(fs*x + phase);
            // ==================================================  # <- added
            //float normalized_x = x / width;  // Normalize x by the stimulus width
            //float normalized_y = y / width;  // Normalize y by the stimulus width
            //float c = m * contr * sin(fs * (normalized_x * cos(theta) + normalized_y * sin(theta)) + phase);
            // ==================================================
            float c = m*contr*sin(fs*(x*cos(theta)+y*sin(theta)) + phase);
            if (box == 1.0) {
                gl_FragColor.rgba = vec4(lum2image(c),1.0);
            } else {
                c = bg + c/2.0;
                gl_FragColor.rgba = vec4(c,c,c,1.0);
            }
        }
        """
    # m = exp(-0.5*(x*x + y*y)/pow(0.17,2.0));
    # abs(sin(fs*x)+phase)
    # float Sde = 0.1;
    # double pi = 2 * acos(0.0);
    # m = (1/(2*pi*pow(Sde,2)))*exp(-(pow(x,2)+pow(y,2))/(2*pow(Sde,2)))

    def __init__(self, posCentre, pos, fileParamsMain, fileParams, fileADM_condition, filesDataMain, params=Params()):
        self.pos = pos
        self.posCentre = posCentre
        self.params = copy_params(self._defaults, params)
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms = dict(map(self.shader.uniform,
                                 ['fs', 'phase', 'contr', 'theta', 'bg', 'box', 'Lbg',
                                  'Lmin', 'Lmax', 'gamma', 'BTRR', 'SdeX', 'SdeY']))  # <- added

        self.fileParams = fileParams
        self.filesDataMain = filesDataMain
        self.fileADM_cond = fileADM_condition
        self.fileParamsMain = fileParamsMain

        glUseProgram(self.program)
        glUniform1f(self.uniforms['phase'], 0.0)
        glUniform1f(self.uniforms['fs'], self.params.fs)
        glUniform1f(self.uniforms['contr'], self.params.contr)
        glUniform1f(self.uniforms['theta'], self.params.theta)
        glUniform1f(self.uniforms['bg'], self.params.bg)
        glUniform1f(self.uniforms['box'], self.params.box)
        glUniform1f(self.uniforms['Lbg'], self.params.Lbg)
        glUniform1f(self.uniforms['Lmin'], self.params.Lmin)
        glUniform1f(self.uniforms['Lmax'], self.params.Lmax)
        glUniform1f(self.uniforms['gamma'], self.params.gamma)
        glUniform1f(self.uniforms['BTRR'], self.params.BTRR)
        glUniform1f(self.uniforms['SdeX'], self.params.SdeX)  # <- added
        glUniform1f(self.uniforms['SdeY'], self.params.SdeY)  # <- added
        glUseProgram(0)

    def draw(self):
        import Functions.functionUSE as funcs
        self.px = self.pos[0]
        self.py = self.pos[1]
        dataParamsMain = funcs.from_Text(self.fileParamsMain)
        condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        admTEXT = dataParamsMain[0]
        dataParams = from_Text(self.fileParams)

        bkg_contrast = dataParams[12]
        max_contrast = dataParams[13]

        conditionVALUE = condition_dictionary[1]
        kwargs = {
            'frequency': conditionVALUE[0], 'position': conditionVALUE[1]}

        self.px = float(kwargs['position'])
        fs = float(kwargs['frequency'])

        cL = funcs.adMethod_luminance_ID(
            admTEXT, self.fileParams, self.filesDataMain)
        self.params.fs = fs

        bkg_Lum_intensity, max_Lum_intensity = bkg_contrast, max_contrast
        cL = funcs.weberContrast(
            [cL], bkg_Lum_intensity, max_Lum_intensity, np.log10, False)[0]
        self.params.contr = cL  # <-- actually give contrast value

        glUseProgram(self.program)
        glUniform1f(self.uniforms['fs'],   self.params.fs)
        glUniform1f(self.uniforms['contr'], self.params.contr)
        glUseProgram(0)

        p = self.params
        x, y = self.pos
        w2 = p.width/2.0
        glUseProgram(self.program)
        ph = p.speed*(self.clock.time()-self.t0)
        glUniform1f(self.uniforms['phase'], ph)
        # glUniform1f(self.uniforms['width'], p.width)  # Update width uniform  # <- added

        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)


class Grating_ADM_new(stim(width=200.0, fs=10.0, ph=0.0, speed=0.0, contr=1.0, theta=0.0, bg=0.5,
                           box=False, Lbg=24.65, Lmin=0.0, Lmax=49.3, gamma=2.5, BTRR=63.2, SdeX=0.03, SdeY=0.03)):
    """Grating stimulus
    
    :param width: size of stimulus in pixels
    :param fs: spatial frequncy
    :param ph: phase
    :param speed: speed
    :param contr: contrast  
    """
    frag_source = """
        //precision highp float;
        
        uniform float fs;
        uniform float phase;
        uniform float contr;
        uniform float bg;
        uniform float box;
        uniform float theta;
        uniform float Lbg, Lmin, Lmax, gamma, BTRR;
        //uniform float width;  // Declare width uniform  # <- added
        uniform float SdeX;
        uniform float SdeY;
        
        vec3 lum2image(float c) {
            vec3 vout;
            float U = 255.0*pow(((1+c)*Lbg-Lmin)/(Lmax-Lmin),1.0/gamma);
            float b1 = (BTRR+1.0)/BTRR;
            //float b = min(floor(U*b1),255.0);
            float b = min(floor(U*b1),255.0) + 1.0/32.0;
            //float b2 = floor((U-b/b1)*(BTRR+1.0));
            float b2 = floor((U-b/b1)*(BTRR+1.0)) + 1.0/32.0;
            vout = vec3(b2/255.0, 0.0 ,b/255.0);
            return vout;
        }

        void main() {
            float x = gl_TexCoord[0].x - 0.5;
            float y = -(gl_TexCoord[0].y - 0.5);
            float pi = 2.0 * acos(0.0);
            //float Sde = 0.03; // 0.05 or 0.17 | USE: Sde = 0.03
            //float m = exp(-0.5*(x*x + y*y)/pow(Sde,2)); // <- 2 or 2.5
            float m = exp(-0.5*((x*x)/pow(SdeX,2) + (y*y)/pow(SdeY,2))); // <- 2 or 2.5
            
            //float m = (1.0/(2.0*pi*pow(Sde,2.0)))*exp(-(pow(x,2.0)+pow(y,2.0))/(2.0*pow(Sde,2.0))); 
            //float m = abs(sin(fs*x)+phase);
            //float c = m*contr*cos(fs*x + phase);
            
            // ==================================================  # <- added
            //float normalized_x = x / width;  // Normalize x by the stimulus width
            //float normalized_y = y / width;  // Normalize y by the stimulus width
            //float c = m * contr * sin(fs * (normalized_x * cos(theta) + normalized_y * sin(theta)) + phase);
            // ==================================================
            
            float c = m*contr*sin(fs*(x*cos(theta)+y*sin(theta)) + phase);
            if (box == 1.0) {
                gl_FragColor.rgba = vec4(lum2image(c),1.0);
            } else {
                c = bg + c/2.0;
                gl_FragColor.rgba = vec4(c,c,c,1.0);
            }
        }
        """
    # m = exp(-0.5*(x*x + y*y)/pow(0.17,2.0));
    # abs(sin(fs*x)+phase)
    # float Sde = 0.1;
    # double pi = 2 * acos(0.0);
    # m = (1/(2*pi*pow(Sde,2)))*exp(-(pow(x,2)+pow(y,2))/(2*pow(Sde,2)))

    def __init__(self, posCentre, pos, fileParamsMain, fileParams, fileADM_condition, filesDataMain, params=Params(), params1=Params()):
        self.pos = pos
        self.posCentre = posCentre
        self.params = copy_params(self._defaults, params)
        self.params1 = copy_params(self._defaults, params1)
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms = dict(map(self.shader.uniform,
                                 ['fs', 'phase', 'contr', 'theta', 'bg', 'box', 'Lbg',
                                  'Lmin', 'Lmax', 'gamma', 'BTRR', 'SdeX', 'SdeY']))  # <- added

        self.fileParams = fileParams
        self.filesDataMain = filesDataMain
        self.fileADM_cond = fileADM_condition
        self.fileParamsMain = fileParamsMain

        glUseProgram(self.program)
        glUniform1f(self.uniforms['phase'], 0.0)
        glUniform1f(self.uniforms['fs'], self.params.fs)
        glUniform1f(self.uniforms['contr'], self.params.contr)
        glUniform1f(self.uniforms['theta'], self.params.theta)
        glUniform1f(self.uniforms['bg'], self.params.bg)
        glUniform1f(self.uniforms['box'], self.params.box)
        glUniform1f(self.uniforms['Lbg'], self.params.Lbg)
        glUniform1f(self.uniforms['Lmin'], self.params.Lmin)
        glUniform1f(self.uniforms['Lmax'], self.params.Lmax)
        glUniform1f(self.uniforms['gamma'], self.params.gamma)
        glUniform1f(self.uniforms['BTRR'], self.params.BTRR)
        glUniform1f(self.uniforms['SdeX'], self.params.SdeX)  # <- added
        glUniform1f(self.uniforms['SdeY'], self.params.SdeY)  # <- added
        glUseProgram(0)

    def draw(self):
        import Functions.functionUSE as funcs
        self.px = self.pos[0]
        self.py = self.pos[1]
        dataParamsMain = funcs.from_Text(self.fileParamsMain)
        condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        admTEXT = dataParamsMain[0]
        dataParams = from_Text(self.fileParams)

        bkg_contrast = dataParams[12]
        max_contrast = dataParams[13]

        conditionVALUE = condition_dictionary[1]
        kwargs = {
            'frequency': conditionVALUE[0], 'position': conditionVALUE[1]}

        self.px = float(kwargs['position'])
        # fs                  = float(kwargs['frequency'])

        cL = funcs.adMethod_luminance_ID(
            admTEXT, self.fileParams, self.filesDataMain)
        # self.params.fs      = fs

        bkg_Lum_intensity, max_Lum_intensity = bkg_contrast, max_contrast
        cL = funcs.weberContrast(
            [cL], bkg_Lum_intensity, max_Lum_intensity, np.log10, False)[0]
        self.params.contr = cL  # <-- actually give contrast value

        self.params1.msg = ('cpu fs: '+str(self.params.fs) +
                            ' cpd fs: '+str(self.params.fs/31.5))
        msg2 = ' sdeX:'+str(round(self.params.SdeX, 5)) + \
            ' sdeY:'+str(round(self.params.SdeY, 5))
        self.label = text.Label(self.params1.msg,
                                font_name='Times New Roman',
                                font_size=self.params1.size,
                                anchor_x='center',
                                anchor_y='center',
                                x=self.pos[0], y=self.pos[1]+self.params.width//4)

        self.label2 = text.Label(msg2,
                                 font_name='Times New Roman',
                                 font_size=self.params1.size,
                                 anchor_x='center',
                                 anchor_y='center',
                                 x=self.pos[0], y=self.pos[1]-20+self.params.width//4)

        glUseProgram(self.program)
        glUniform1f(self.uniforms['fs'],   self.params.fs)
        glUniform1f(self.uniforms['contr'], self.params.contr)
        glUseProgram(0)

        p = self.params
        x, y = self.pos
        w2 = p.width/2.0
        glUseProgram(self.program)
        ph = p.speed*(self.clock.time()-self.t0)
        glUniform1f(self.uniforms['phase'], ph)
        # glUniform1f(self.uniforms['width'], p.width)  # Update width uniform  # <- added

        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)

        # add text cpu luminance ====
        glEnable(GL_BLEND)
        glEnable(GL_TEXTURE_2D)
        self.label.draw()
        self.label2.draw()


# class unit_test(stim(pixel_widthx=1900,pixel_heighty= 800,win_widthx=1900, win_widthy=800, flanker_dx=0.5, flanker_width=5.0)):
#     """
#     Unit test, check pixel to meter ratio. Arc visual angle.
#     """
#     def __init__(self, monitor_z0, params=Params()):
#         import Functions.functionUSE as funcs

#         self.params 		= copy_params(self._defaults,params)
#         self.monitor_z0 	= monitor_z0
#         self.pixel_heighty  = self.params.pixel_heighty
#         self.pixel_widthx   = self.params.pixel_widthx
#         self.win_widthx		= self.params.win_widthx
#         self.win_widthy		= self.params.win_widthy
#         self.flanker_dx		= self.params.flanker_dx    # flanker displacement
#         self.flanker_width 	= self.params.flanker_width # flanker width

#         #self.pixel_metre_ratio	 = funcs.ratio_PIXEL_Meter(self.pixel_widthx, self.pixel_heighty, self.win_widthx, self.win_widthy)
#         self.pixel_FLANKER_dx0	 = funcs.convertArcangleTOPixel(self.flanker_dx, self.monitor_z0, self.pixel_metre_ratio)
#         self.pixel_flanker_width = funcs.convertArcangleTOPixel(self.flanker_width, self.monitor_z0, self.pixel_metre_ratio)


#     def check_pixelMetre_ratio(self):
#         import Functions.functionUSE as funcs
#         print(' # ========== # ')
#         """ Pixel: """
#         print('max x axis value:', self.win_widthx)
#         print('max y axis value:', self.win_widthy)
#         print(' # ========== # ')
#         """Pixels:"""
#         arcAngle      = 0.5
#         print('arc angle 0.5:', arcAngle)
#         posRatioPixel = (np.tan(np.radians(arcAngle))*self.monitor_z0)/(self.pixel_metre_ratio)
#         print('pos_Pixel:',posRatioPixel)
#         print(' # ========== # ')
#         """Meters:"""
#         posRatioMeter = (np.tan(np.radians(arcAngle))*self.monitor_z0)
#         print('pos_Meter: ',posRatioMeter)
#         print('arc angle 0.5 == ', funcs.Meter_convertToArcangle(posRatioMeter, self.monitor_z0, self.pixel_metre_ratio))

#         print(' # ========== # ')
#         print('one pixel = metre: ', 		    self.pixel_metre_ratio)
#         print(r"Displacement from $x_{0}$ arc $ \theta $:",(self.flanker_dx))
#         print('Displacement from centre x (m):',np.tan(np.radians(self.flanker_dx))*(self.monitor_z0))
#         print('Displacement from centre pixel:',self.pixel_FLANKER_dx0)

#         print(' # ========== # ')
#         print('Width of flanker arcAngle:', self.flanker_width)
#         print('Width of flanker metre:',    np.tan(np.radians(self.flanker_width))*(self.monitor_z0))
#         print('Width of flanker pixel:',    self.pixel_flanker_width)
#         print('Width of Grating in metre:', funcs.arcAngleTO_meter(self.flanker_width, self.monitor_z0))
#
#


class Line_MeasureCPD(stim(length=100.0, width=10.0, angle=0.0, color=(1.0, 1.0, 1.0, 1.0))):
    def __init__(self, pos, fileParams, params=Params()):
        self.pos = pos
        self.fileParams = fileParams
        self.params = copy_params(self._defaults, params)

    def draw(self):
        dataParams = from_Text(self.fileParams)
        checkKeyCount = dataParams[3]
        pixelX, pixelY = dataParams[1], dataParams[2]
        pixelLength = dataParams[4]

        if checkKeyCount == 1:
            import Functions.functionUSE as funcs
            # dataParams      = from_Text(self.fileParams)
            valueKey = dataParams[0]
            distance_To_Monitor = dataParams[5]
            pixel_metre_ratio = dataParams[6]
            deg1PCD = dataParams[7]
            movePosX = 0
            movePosY = 0
            addlength = 0
            if int(valueKey) == 1:
                movePosX = +10
            elif int(valueKey) == -1:
                movePosX = -5
            elif int(valueKey) == 2:
                movePosY = +10
            elif int(valueKey) == -2:
                movePosY = -10
            elif int(valueKey) == 3:
                addlength = +10
            elif int(valueKey) == -3:
                addlength = -2
            else:
                pass
            pixelX = int(pixelX+movePosX)  # +self.pos[0]
            pixelY = int(pixelY+movePosY)  # +self.pos[1]
            pixelLength = int(pixelLength+addlength)
            lengthDegree = funcs.convertPixelToArcangle(
                pixelLength, distance_To_Monitor, pixel_metre_ratio)
            print('#============#')
            print('lengthDegree :', lengthDegree)
            print('pixelLength  :', pixelLength)
            print('pixelX       :', pixelX)
            print('valueKey     :', valueKey)
            print('deg1PCD      :', deg1PCD)
            print('#============#')
            dataParams[1] = int(pixelX)
            dataParams[2] = int(pixelY)
            checkKeyCount = 0
            dataParams[3] = checkKeyCount
            dataParams[4] = pixelLength
            to_Text(self.fileParams,       dataParams)
        elif checkKeyCount == 0:
            pass
        # === ... ===
        cL = 1.0
        self.params.color = (cL, cL, cL, 1.0)
        # params.color):
        if hasattr(self.params, 'color') and not iterable(self.params.color):
            self.params.color = [self.params.color]*3
        self.params = copy_params(self._defaults, self.params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy                  = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[pixelLength, p.width]  # p.length, p.width
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(pixelX, pixelY, 0.0)
        glRotatef(self.params.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()

# ========================================================
# ========================================================
# ========================================================
# ========================================================
# ========================================================

# sound_cache = {}


class Sound_dot(stim(wavefile=None)):
    """Sound stimulus
    
    :param wavefile: filename of sound file to be played
    """

    def __init__(self, pos, params=Params(), params0=Params()):
        sound_cache = {}
        self.pos = pos
        self.params = copy_params(self._defaults, params)
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # load pyglet sound object
        if self.params.wavefile not in sound_cache:
            sound_cache[self.params.wavefile] = pyglet.media.load(
                self.params.wavefile)
        self.sound = sound_cache[self.params.wavefile]
        self.played = False

        self.params0 = copy_params(self._defaults, params0)
        sigma = self.params0.sigma
        fs = self.params0.fs
        phi = self.params0.phi
        edge = self.params0.edge
        res = self.params0.res

        im = make_dot(sigma, fs, phi, edge, res)  # <-type of stimulus
        w = im.width
        h = im.height
        im.anchor_x = w//2
        im.anchor_y = h//2
        self.image = im
        self.pos = pos

    def draw(self):
        p = self.params
        # play sound
        if not self.played:
            self.sound.play()
            self.played = True

        c = self.params0.c
        glColor4f(c, c, c, 1.0)
        self.image.blit(self.pos[0], self.pos[1])


class Dot_StairCase(stim(c=1.0, sigma=0.17, fs=0.0, phi=0.0, edge=2.0, res=64)):
    """Gaussian dot stimulus with size control
    
    :param c: contrast [0.0,1.0]
    """

    def __init__(self, pos, params=Params()):
        self.params = copy_params(self._defaults, params)
        sigma = self.params.sigma
        fs = self.params.fs
        phi = self.params.phi
        edge = self.params.edge
        res = self.params.res

        im = make_dot(sigma, fs, phi, edge, res)  # <-type of stimulus
        w = im.width
        h = im.height
        im.anchor_x = w//2
        im.anchor_y = h//2
        self.image = im
        self.pos = pos

    def draw(self):
        c = self.params.c
        glColor4f(c, c, c, 1.0)
        self.image.blit(self.pos[0], self.pos[1])


class Dot_Size_right(stim(c=1.0, sigma=0.17, fs=0.0, phi=0.0, edge=2.0, res=64)):
    """Gaussian dot stimulus with size control
    
    :param c: contrast [0.0,1.0]
    """

    def __init__(self, pos, pos2, posCentre, params=Params(), params0=Params()):
        self.params = copy_params(self._defaults, params)
        sigma = self.params.sigma
        fs = self.params.fs
        phi = self.params.phi
        edge = self.params.edge
        res = self.params.res

        self.params0 = copy_params(self._defaults, params0)
        sigma0 = self.params0.sigma
        fs0 = self.params0.fs
        phi0 = self.params0.phi
        edge0 = self.params0.edge
        res0 = self.params0.res

        im = make_dot(sigma, fs, phi, edge, res)  # <-type of stimulus
        im2 = make_dot(sigma0, fs0, phi0, edge0, res0)  # <-type of stimulus

        w = im.width
        h = im.height
        im.anchor_x = w//2
        im.anchor_y = h//2

        w = im2.width
        h = im2.height
        im2.anchor_x = w//2
        im2.anchor_y = h//2

        self.image0 = im
        self.image2 = im2
        self.pos = pos
        self.pos2 = pos2
        self.posCentre = posCentre

    def sound(self):
        frequency = 500  # Set Frequency To 2500 Hertz
        duration = 500  # Set Duration To 1000 ms == 1 second
        winsound.Beep(frequency, duration)

    def draw(self):
        # self.sound()

        c = self.params.c
        glColor4f(c, c, c, 1.0)
        self.image0.blit(self.pos2[0], self.pos2[1])  # <- add second stimulus
        c2 = 0.05
        glColor4f(c2, c2, c2, 1.0)
        # <- add second stimulus
        self.image2.blit(self.posCentre[0], self.posCentre[1])


class Dot_Size_left(stim(c=1.0, sigma=0.17, fs=0.0, phi=0.0, edge=2.0, res=64)):
    """Gaussian dot stimulus with size control
    
    :param c: contrast [0.0,1.0]
    """

    def __init__(self, pos, pos2, posCentre, params=Params(), params0=Params()):
        self.params = copy_params(self._defaults, params)
        sigma = self.params.sigma
        fs = self.params.fs
        phi = self.params.phi
        edge = self.params.edge
        res = self.params.res

        self.params0 = copy_params(self._defaults, params0)
        sigma0 = self.params0.sigma
        fs0 = self.params0.fs
        phi0 = self.params0.phi
        edge0 = self.params0.edge
        res0 = self.params0.res

        im = make_dot(sigma, fs, phi, edge, res)  # <-type of stimulus
        im2 = make_dot(sigma0, fs0, phi0, edge0, res0)  # <-type of stimulus

        w = im.width
        h = im.height
        im.anchor_x = w//2
        im.anchor_y = h//2

        w = im2.width
        h = im2.height
        im2.anchor_x = w//2
        im2.anchor_y = h//2

        self.image0 = im
        self.image2 = im2
        self.pos = pos
        self.pos2 = pos2
        self.posCentre = posCentre

    def sound(self):
        frequency = 500  # Set Frequency To 2500 Hertz
        duration = 500  # Set Duration To 1000 ms == 1 second
        winsound.Beep(frequency, duration)

    def draw(self):
        # self.sound()

        c = self.params.c
        glColor4f(c, c, c, 1.0)
        self.image0.blit(self.pos[0], self.pos[1])
        c2 = 0.05
        glColor4f(c2, c2, c2, 1.0)
        # <- add second stimulus
        self.image2.blit(self.posCentre[0], self.posCentre[1])

# ============= staircase ==================== below ===================


class Dot_staircase_right(stim(c=1.0, sigma=0.17, fs=0.0, phi=0.0, edge=2.0, res=64)):
    """Gaussian dot stimulus with size control
    
    :param c: contrast [0.0,1.0]
    """

    def __init__(self, bkg, filesData, pos, pos2, posCentre, params=Params(), params0=Params()):
        self.params = copy_params(self._defaults, params)
        self.filesData = filesData
        self.params.bkg = bkg

        bgk = self.params.bkg
        sigma = self.params.sigma
        fs = self.params.fs
        phi = self.params.phi
        edge = self.params.edge
        res = self.params.res

        self.params0 = copy_params(self._defaults, params0)
        sigma0 = self.params0.sigma
        fs0 = self.params0.fs
        phi0 = self.params0.phi
        edge0 = self.params0.edge
        res0 = self.params0.res

        im = make_dot(sigma, fs, phi, edge, res)  # <-type of stimulus
        im2 = make_dot(sigma0, fs0, phi0, edge0, res0)  # <-type of stimulus

        w = im.width
        h = im.height
        im.anchor_x = w//2
        im.anchor_y = h//2

        w = im2.width
        h = im2.height
        im2.anchor_x = w//2
        im2.anchor_y = h//2

        self.image0 = im
        self.image2 = im2
        self.pos = pos
        self.pos2 = pos2
        self.posCentre = posCentre

    def memory(self):
        # =========================================
        # =========================================
        global cL_param
        wb = pyxl.load_workbook(filename=self.filesData)
        ws = wb.worksheets[0]
        rowMax = ws.max_row

        if rowMax > 3:
            base_cL = self.params.bkg  # ws.cell(row=rowMax-1, column=9).value
            minR = rowMax-4
            step_up = ws.cell(row=rowMax-1, column=10).value
            step_dw = ws.cell(row=rowMax-1, column=11).value
            step_dwL = ws.cell(row=rowMax-1, column=12).value
        elif rowMax <= 3 and rowMax > 1:
            # base_cL = ws.cell(row=rowMax-1, column=9).value
            minR = rowMax-1
            base_cL = self.params.bkg
            step_up = 0.02
            step_dw = -0.02
            step_dwL = -0.1
        elif rowMax <= 1:
            minR = 0
            base_cL = self.params.bkg
            step_up = 0.02
            step_dw = -0.02
            step_dwL = -0.1

        if minR != 0:
            count = 0
            for j in range(minR, rowMax, 1):
                probe_LR = ws.cell(row=j+1, column=2).value
                human_LR = ws.cell(row=j+1, column=7).value

                if probe_LR == human_LR:
                    count += -1
                elif probe_LR != human_LR:
                    count += +1

            if count >= 2:
                cL_param = step_up+base_cL
                step_dw = step_dw/2.0
                step_dwL = step_dwL/2.0
            elif count < 0:
                cL_param = step_dw+base_cL
            elif count < 2 and count >= 0:
                step_up/2.0
                cL_param = step_dwL+base_cL

            for i in range(1):
                if cL_param >= 1.0:
                    cL_param = 1.0
                elif cL_param <= self.params.bkg:
                    cL_param = self.params.bkg
                else:
                    continue

        elif minR == 0:
            count = 0
            cL_param = self.params.c

        ws.cell(row=rowMax, column=10).value = step_up
        ws.cell(row=rowMax, column=11).value = step_dw
        ws.cell(row=rowMax, column=12).value = step_dwL
        ws.cell(row=rowMax, column=9).value = cL_param
        ws.cell(row=rowMax, column=10).value = count
        wb.save(self.filesData)
        # =========================================
        # =========================================
        return cL_param

    def draw(self):
        c = self.memory()
        glColor4f(c, c, c, 1.0)
        self.image0.blit(self.pos2[0], self.pos2[1])  # <- add second stimulus
        c2 = 0.45
        glColor4f(c2, c2, c2, 1.0)
        # <- add second stimulus
        self.image2.blit(self.posCentre[0], self.posCentre[1])


class Dot_staircase_left(stim(c=1.0, sigma=0.17, fs=0.0, phi=0.0, edge=2.0, res=64)):
    """Gaussian dot stimulus with size control
    
    :param c: contrast [0.0,1.0]
    """

    def __init__(self, fileHuman, fileProbe, fileParams, filesData,
                 pos, posCentre, params=Params(), params0=Params()):
        self.params = copy_params(self._defaults, params)
        self.filesData = filesData
        self.fileHuman = fileHuman
        self.fileProbe = fileProbe
        self.fileParams = fileParams

        sigma = self.params.sigma
        fs = self.params.fs
        phi = self.params.phi
        edge = self.params.edge
        res = self.params.res

        self.params0 = copy_params(self._defaults, params0)
        sigma0 = self.params0.sigma
        fs0 = self.params0.fs
        phi0 = self.params0.phi
        edge0 = self.params0.edge
        res0 = self.params0.res

        dataParams = from_Text(self.fileParams)
        dataProbeA = from_Text(self.fileProbe)
        dataHumanA = from_Text(self.fileHuman)

        self.dataParams = dataParams
        self.dataProbeA = dataProbeA
        self.dataHumanA = dataHumanA

        im = make_dot(sigma, fs, phi, edge, res)  # <-type of stimulus
        im2 = make_dot(sigma0, fs0, phi0, edge0, res0)  # <-type of stimulus

        w = im.width
        h = im.height
        im.anchor_x = w//2
        im.anchor_y = h//2

        w = im2.width
        h = im2.height
        im2.anchor_x = w//2
        im2.anchor_y = h//2

        self.image0 = im
        self.image2 = im2
        self.pos = pos
        self.posCentre = posCentre

    def draw(self):
        cL = from_Text(self.fileParams)[0]  # self.dataParams[0]
        glColor4f(cL, cL, cL, 1.0)
        self.image0.blit(self.pos[0], self.pos[1])
        c2 = self.params0.c
        glColor4f(c2, c2, c2, 1.0)
        # <- add second stimulus
        self.image2.blit(self.posCentre[0], self.posCentre[1])


class Text_termination(stim(msg='Text', size=24)):
    """Text stimulus
    
    :param msg: string to display
    :params size: font size (default 24)
    """

    def __init__(self, pos, params=Params()):
        self.params = copy_params(self._defaults, params)
        self.pos = pos
        p = self.params
        self.label = text.Label(p.msg,
                                font_name='Times New Roman',
                                font_size=p.size,
                                anchor_x='center',
                                anchor_y='center',
                                x=pos[0], y=pos[1])

    def draw(self):
        glEnable(GL_BLEND)
        glEnable(GL_TEXTURE_2D)
        self.label.draw()


class Dot_stairCase_centre(stim(c=1.0, sigma=0.17, fs=0.0, phi=0.0, edge=2.0, res=64, msg='Text', size=24)):
    """Gaussian dot stimulus with size control
    
    :param c: contrast [0.0,1.0]
    """

    def __init__(self, bkg, filename_params, filesData, posCentre, params=Params()):
        self.params = copy_params(self._defaults, params)
        self.filesData = filesData
        self.fileParams = filename_params
        self.params.bkg = bkg

        self.params = copy_params(self._defaults, params)
        self.pos = posCentre
        p = self.params
        self.label = text.Label(p.msg,
                                font_name='Times New Roman',
                                font_size=p.size,
                                anchor_x='center',
                                anchor_y='center',
                                x=self.pos[0], y=self.pos[1])

        sigma = self.params.sigma
        fs = self.params.fs
        phi = self.params.phi
        edge = self.params.edge
        res = self.params.res
        im = make_dot(sigma, fs, phi, edge, res)  # <-type of stimulus

        w = im.width
        h = im.height
        im.anchor_x = w//2
        im.anchor_y = h//2

        self.image0 = im
        self.posCentre = posCentre

    def draw(self):
        FILEparams = from_Text(self.fileParams)
        terminateBOOL = int(FILEparams[20])
        if terminateBOOL == 0:
            c2 = self.params.c
            glColor4f(c2, c2, c2, 1.0)
            # <- add second stimulus
            self.image0.blit(self.posCentre[0], self.posCentre[1])
        elif terminateBOOL == 1:
            glEnable(GL_BLEND)
            glEnable(GL_TEXTURE_2D)
            self.label.draw()
        else:
            c2 = self.params.c
            glColor4f(c2, c2, c2, 1.0)
            # <- add second stimulus
            self.image0.blit(self.posCentre[0], self.posCentre[1])


class Dot_stairCase_centre_beep(stim(c=1.0, sigma=0.17, fs=0.0, phi=0.0, edge=2.0, res=64, msg='Text', size=24)):
    """Gaussian dot stimulus with size control
    
    :param c: contrast [0.0,1.0]
    """

    def __init__(self, bkg, filename_params, filesData, posCentre, params=Params()):
        self.params = copy_params(self._defaults, params)
        self.filesData = filesData
        self.fileParams = filename_params
        self.params.bkg = bkg

        self.params = copy_params(self._defaults, params)
        self.pos = posCentre
        p = self.params
        self.label = text.Label(p.msg,
                                font_name='Times New Roman',
                                font_size=p.size,
                                anchor_x='center',
                                anchor_y='center',
                                x=self.pos[0], y=self.pos[1])

        sigma = self.params.sigma
        fs = self.params.fs
        phi = self.params.phi
        edge = self.params.edge
        res = self.params.res
        im = make_dot(sigma, fs, phi, edge, res)  # <-type of stimulus

        w = im.width
        h = im.height
        im.anchor_x = w//2
        im.anchor_y = h//2

        self.image0 = im
        self.posCentre = posCentre

    def draw(self):
        FILEparams = from_Text(self.fileParams)
        terminateBOOL = int(FILEparams[20])
        import winsound
        duration = 17
        frequency = 550
        winsound.Beep(frequency, duration)
        if terminateBOOL == 0:
            c2 = self.params.c
            glColor4f(c2, c2, c2, 1.0)
            # <- add second stimulus
            self.image0.blit(self.posCentre[0], self.posCentre[1])
        elif terminateBOOL == 1:
            glEnable(GL_BLEND)
            glEnable(GL_TEXTURE_2D)
            self.label.draw()
        else:
            c2 = self.params.c
            glColor4f(c2, c2, c2, 1.0)
            # <- add second stimulus
            self.image0.blit(self.posCentre[0], self.posCentre[1])


"""
||$||
"""


class Dot_Termination_criteria(stim(c=1.0, sigma=0.17, fs=0.0, phi=0.0, edge=2.0, res=64)):
    """Gaussian dot stimulus with size control
    
    :param c: contrast [0.0,1.0]
    """

    def __init__(self, bkg, filesData, posCentre, params=Params()):
        self.params = copy_params(self._defaults, params)
        self.filesData = filesData
        self.params.bkg = bkg

        sigma = self.params.sigma
        fs = self.params.fs
        phi = self.params.phi
        edge = self.params.edge
        res = self.params.res
        im = make_dot(sigma, fs, phi, edge, res)  # <-type of stimulus

        w = im.width
        h = im.height
        im.anchor_x = w//2
        im.anchor_y = h//2

        self.image0 = im
        self.posCentre = posCentre

    def draw(self):
        c2 = self.params.c
        glColor4f(c2, c2, c2, 1.0)
        # <- add second stimulus
        self.image0.blit(self.posCentre[0], self.posCentre[1])


# ================== line ================= stim =====
class Line_const_LR(stim(length=100.0, width=10.0, angle=0.0, color=(1.0, 1.0, 1.0, 1.0))):
    def __init__(self, probe_crt, pos, posCentre, params=Params(), params0=Params()):
        self.pos = pos
        self.probe_crt = probe_crt

        self.params0 = copy_params(self._defaults, params0)
        sigma0 = self.params0.sigma
        fs0 = self.params0.fs
        phi0 = self.params0.phi
        edge0 = self.params0.edge
        res0 = self.params0.res

        im0 = make_dot(sigma0, fs0, phi0, edge0, res0)  # <-type of stimulus

        w = im0.width
        h = im0.height
        im0.anchor_x = w//2
        im0.anchor_y = h//2

        self.image0 = im0
        self.posCentre = posCentre

        if hasattr(params, 'color') and not iterable(params.color):
            params.color = [params.color]*3
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.length, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

    def draw(self):
        # self.sound()
        c2 = self.probe_crt
        glColor4f(c2, c2, c2, 1.0)
        self.image0.blit(self.posCentre[0], self.posCentre[1])

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.params.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()


class Line_staircase_LR(stim(length=100.0, width=10.0, angle=0.0, color=(1.0, 1.0, 1.0, 1.0))):
    def __init__(self, fileHuman, fileProbe, fileParams, filesData, bkg, fixation_crt,
                 pos, posCentre, params=Params(), params0=Params()):  # , params1=Params()):
        self.pos = pos
        self.filesData = filesData
        self.fileHuman = fileHuman
        self.fileProbe = fileProbe
        self.fileParams = fileParams
        self.fixation_crt = fixation_crt
        self.bkg = bkg

        self.params = copy_params(self._defaults, params)
        self.params0 = copy_params(self._defaults, params0)
        sigma0 = self.params0.sigma
        fs0 = self.params0.fs
        phi0 = self.params0.phi
        edge0 = self.params0.edge
        res0 = self.params0.res

        # dataParams = from_Text(self.fileParams)
        dataProbeA = from_Text(self.fileProbe)
        # self.dataParams = dataParams
        self.dataProbeA = dataProbeA

        im0 = make_dot(sigma0, fs0, phi0, edge0, res0)
        w = im0.width
        h = im0.height
        im0.anchor_x = w//2
        im0.anchor_y = h//2

        self.image0 = im0
        self.posCentre = posCentre

        # cL = from_Text(self.fileParams)[0]
        # self.params.color= (cL,cL,cL,1.0)

    def draw(self):
        c2 = self.fixation_crt
        glColor4f(c2, c2, c2, 1.0)
        self.image0.blit(self.posCentre[0], self.posCentre[1])

        cL = from_Text(self.fileParams)[0]
        self.params.color = (cL, cL, cL, 1.0)

        # params.color):
        if hasattr(self.params, 'color') and not iterable(self.params.color):
            self.params.color = [self.params.color]*3
        self.params = copy_params(self._defaults, self.params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy  = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.length, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.params.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()


class EllipseCircle2D(stim(th=0.0, R=50.0, d=3.0, alpha=1.0, a=10.0, b=10.0, width=0.5, bkg=0.0, diff_bkg=0.018)):
    """Orientation circle stimulus
    
    :param th: size of stimulus
    :param R: radius
    :param d: width of orientation bar
    :param width: width of ellipse
    :param diff_bkg: difference added to background contrast
    """
    frag_source = """
    uniform float th, sigma, gap, alpha, a, b, width, bkg, diff_bkg;
    float edge = 40.0;

    float lined(float t, float x, float y) {
        return abs(-sin(t)*x+cos(t)*y);
    }

    float g(float x, float s2, float e2) {
        return exp(-0.5*pow(abs(x)/s2,e2));
    }
    
    void main( void ) {
        float x = gl_TexCoord[0].x - 0.5;
        float y = -(gl_TexCoord[0].y - 0.5);
        
        
        // Compute the ellipse equation
        float ellipse = (x*x) / (a*a) + (y*y) / (b*b);

        // Define outer and inner boundaries
        float outerBoundary = 1.0;
        float innerBoundary = 1.0 - width;  // The "thickness" of the ellipse band

        // Determine if pixel is inside the elliptical ring
        float c = (ellipse <= outerBoundary && ellipse >= innerBoundary) ? bkg+diff_bkg : bkg;


        //float c = smoothstep(0.01, bkg+diff_bkg, outerBoundary - ellipse) - smoothstep(0.01, bkg+diff_bkg, innerBoundary - ellipse);
        gl_FragColor = vec4( c,c,c,alpha );

    }
    """

    def __init__(self, pos, params=Params()):
        self.pos = pos
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms = dict(map(self.shader.uniform, [
                             'th', 'sigma', 'gap', 'alpha', 'a', 'b', 'width', 'bkg', 'diff_bkg']))
        glUseProgram(self.program)
        self.w = p.R*2.5
        glUniform1f(self.uniforms['th'], p.th)
        glUniform1f(self.uniforms['sigma'], 0.4)  # 0.4
        glUniform1f(self.uniforms['gap'], p.d/self.w)
        glUniform1f(self.uniforms['alpha'], p.alpha)
        glUniform1f(self.uniforms['a'], p.a)
        glUniform1f(self.uniforms['b'], p.b)
        glUniform1f(self.uniforms['width'], p.width)
        glUniform1f(self.uniforms['bkg'], p.bkg)
        glUniform1f(self.uniforms['diff_bkg'], p.diff_bkg)
        glUseProgram(0)

    def draw(self):
        p = self.params
        x, y = self.pos
        w2 = self.w/2.0
        glUseProgram(self.program)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)


class EllipseCircle2D_radius(stim(th=0.0, R=50.0, d=3.0, alpha=1.0, a=10.0, b=10.0, width=0.5, bkg=0.0, diff_bkg=0.018, aspect_ratio=1.0, ppd_x=76.6, ppd_y=71.9,
                                  screen_width_pixels=1920.0, screen_height_pixels=1080.0)):
    """Orientation circle stimulus
    
    :param th: size of stimulus
    :param R: radius
    :param d: width of orientation bar
    :param width: width of ellipse
    :param diff_bkg: difference added to background contrast
    """
    frag_source = """
    uniform float th, sigma, gap, alpha, a, b, width, bkg, diff_bkg, aspect_ratio, ppd_x, ppd_y, screen_width_pixels, screen_height_pixels, center_x, center_y;
    float edge = 40.0;

    
    void main( void ) {
        //float x = gl_TexCoord[0].x - 0.5;   // Normalized  Texture Coordinates
        //float y = -(gl_TexCoord[0].y - 0.5);// Normalized  Texture Coordinates

        float x = gl_FragCoord.x; // — Screen Pixel Coordinates
        float y = gl_FragCoord.y; // — Screen Pixel Coordinates

        // Convert texture coordinates to screen pixel coordinates directly
        float x_px = x; // 0 to screen_width_pixels
        float y_px = y; // 0 to screen_height_pixels

        // Convert to degrees of visual angle
        //float x_deg = (x_px - 0.5 * screen_width_pixels) / ppd_x;
        //float y_deg = (y_px - 0.5 * screen_height_pixels-250.0) / ppd_y;

        float x_deg = (x_px - center_x) / ppd_x;
        float y_deg = (y_px - center_y) / ppd_y;
        
        // Polar angle from center
        float theta = atan(y_deg, x_deg);  
        // Radius of ellipse in this direction
        float cos_t = cos(theta);
        float sin_t = sin(theta);
        float ellipse_radius = (a * b) / sqrt((b * cos_t) * (b * cos_t) + (a * sin_t) * (a * sin_t));

        // 3. Normalize by ellipse radii (a, b in degrees)
        //float nx = x_deg / a;
        //float ny = y_deg / b;

        // 4. Compute distance from center in ellipse space
        // float dist = sqrt(nx * nx + ny * ny);

        // Euclidean distance from center
        float dist_deg = sqrt(x_deg * x_deg + y_deg * y_deg);
        
        // 5. Smooth-edged ring at radius 1.0
        float eps = 0.01;
        // float ring = smoothstep(1.0 - width - eps, 1.0 - width + eps, dist) -
        //            smoothstep(1.0 + width - eps, 1.0 + width + eps, dist);

        float ring = smoothstep(ellipse_radius - width - eps, ellipse_radius - width + eps, dist_deg) -
             smoothstep(ellipse_radius + width - eps, ellipse_radius + width + eps, dist_deg);


        // 6. Add ring contrast to background
        float c = bkg + ring * diff_bkg;

        // Compute the smooth step for the outer and inner boundaries
        // This will create a smooth transition between the inner and outer boundaries
        // -> smoothstep(edge0, edge1, x) 
        // -> Returns 0.0 if x <= edge0
        // -> Returns 1.0 if x >= edge1
        // -> Returns a value between 0.0 and 1.0 if edge0 < x < edge1


        gl_FragColor    = vec4( c,c,c,alpha );

    }
    """

    def __init__(self, pos, fileParams, filePosition, params=Params()):
        self.pos = pos
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.fileParams = fileParams
        self.filePosition = filePosition
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms = dict(map(self.shader.uniform, [
                             'th', 'sigma', 'gap', 'alpha', 'a', 'b', 'width', 'bkg',
                             'diff_bkg', 'aspect_ratio', 'ppd_x', 'ppd_y', 'screen_width_pixels', 'screen_height_pixels',
                             'center_x', 'center_y']))
        glUseProgram(self.program)
        self.w = p.R*2.5
        glUniform1f(self.uniforms['th'], p.th)
        glUniform1f(self.uniforms['sigma'], 0.4)  # 0.4
        glUniform1f(self.uniforms['gap'], p.d/self.w)
        glUniform1f(self.uniforms['alpha'], p.alpha)
        glUniform1f(self.uniforms['a'], p.a)
        glUniform1f(self.uniforms['b'], p.b)
        glUniform1f(self.uniforms['center_x'], self.pos[0])
        glUniform1f(self.uniforms['center_y'], self.pos[1])
        glUniform1f(self.uniforms['screen_width_pixels'],
                    p.screen_width_pixels)
        glUniform1f(
            self.uniforms['screen_height_pixels'], p.screen_height_pixels)
        glUniform1f(self.uniforms['width'], p.width)
        glUniform1f(self.uniforms['bkg'], p.bkg)
        glUniform1f(self.uniforms['diff_bkg'], p.diff_bkg)
        glUniform1f(self.uniforms['aspect_ratio'], p.aspect_ratio)
        glUniform1f(self.uniforms['ppd_x'], p.ppd_x)
        glUniform1f(self.uniforms['ppd_y'], p.ppd_y)
        glUseProgram(0)

    def draw(self):
        import Functions.functionUSE as funcs
        dataParams = from_Text(self.fileParams)
        self.dataPosition = from_Text(self.filePosition)
        posx = (self.dataPosition[0])
        distanceToMonitor = dataParams[17]
        pixel_metre_ratio = dataParams[18]
        pxDegree = (funcs.convertPixelToArcangle(
            posx, distanceToMonitor, pixel_metre_ratio))
        p = self.params
        x, y = self.pos
        w2 = self.w/2.0
        glUseProgram(self.program)
        glPushMatrix()
        glLoadIdentity()
        glUniform1f(self.uniforms['b'], pxDegree)
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        # Here we draw the quad rectangle that the stimuluis will be drawn on.
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)


class two_lines_displacement(stim(th=0.0, R=50.0, d=3.0, alpha=1.0, a=10.0, b=10.0, width=0.5, bkg=0.0, diff_bkg=0.018)):
    """Orientation circle stimulus
    
    :param th: size of stimulus
    :param R: radius
    :param d: width of orientation bar
    :param width: width of ellipse
    :param diff_bkg: difference added to background contrast
    """
    frag_source = """
    uniform float th, sigma, gap, alpha, a, b, width, bkg, diff_bkg;
    float edge = 40.0;

    float lined(float t, float x, float y) {
        return abs(-sin(t)*x+cos(t)*y);
    }

    float g(float x, float s2, float e2) {
        return exp(-0.5*pow(abs(x)/s2,e2));
    }
    
    void main( void ) {
        float x = gl_TexCoord[0].x - 0.5;
        float y = -(gl_TexCoord[0].y - 0.5);
        
        
        // Compute the ellipse equation
        float ellipse = (x*x) / (a*a) + (y*y) / (b*b);
        
        // Compute the square equation
        float square_x  = abs(x);
        float square_y  = y;

        float outerBoundary_x = a;
        float innerBoundary_x = a - width; 

        float outerBoundary_y = b;
        float innerBoundary_y = -b; 

        //float c = ((square_x >= outerBoundary_x*(-1.0) && square_x <= innerBoundary_x*(-1.0) && square_y <= outerBoundary_y && square_y >= innerBoundary_y) || (square_x <= outerBoundary_x && square_x >= innerBoundary_x && square_y <= outerBoundary_y && square_y >= innerBoundary_y)) ? diff_bkg : bkg;
        // note ? means if statemnt before is true the continue with ? "" otherwise use : "".
        float c = ((square_x <= outerBoundary_x && square_x >= innerBoundary_x && square_y <= outerBoundary_y && square_y >= innerBoundary_y)) ? diff_bkg : bkg;

        //if ((square_x >= outerBoundary_x*(-1.0) && square_x <= innerBoundary_x*(-1.0) && square_y <= outerBoundary_y && square_y >= innerBoundary_y) || (square_x <= outerBoundary_x && square_x >= innerBoundary_x && square_y <= outerBoundary_y && square_y >= innerBoundary_y)) {
        //    float c =  diff_bkg; 
        //} else {
        //    float c = bkg;
        //}
        gl_FragColor = vec4( c,c,c,alpha );
    }
    """

    def __init__(self, pos, posCentre, fileParams, fileADM_cond, filePosition, params=Params()):
        self.pos = pos
        self.posCentre = posCentre
        self.fileParams = fileParams
        self.filePosition = filePosition
        self.fileADM_cond = fileADM_cond
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms       = dict(map(self.shader.uniform, ['th', 'sigma', 'gap', 'alpha', 'a', 'b', 'width', 'bkg', 'diff_bkg']))
        glUseProgram(self.program)
        self.w = p.R*2.5
        glUniform1f(self.uniforms['th'], p.th)
        glUniform1f(self.uniforms['sigma'], 0.4)  # 0.4
        glUniform1f(self.uniforms['gap'], p.d/self.w)
        glUniform1f(self.uniforms['alpha'], p.alpha)
        glUniform1f(self.uniforms['a'], p.a)
        glUniform1f(self.uniforms['b'], p.b)
        glUniform1f(self.uniforms['width'], p.width)
        glUniform1f(self.uniforms['bkg'], p.bkg)
        glUniform1f(self.uniforms['diff_bkg'], p.diff_bkg)
        glUseProgram(0)

    def draw(self):
        p = self.params
        import Functions.functionUSE as funcs
        dataParams = from_Text(self.fileParams)
        self.dataPosition = from_Text(self.filePosition)
        posx = (self.dataPosition[0])
        distanceToMonitor = dataParams[17]
        pixel_metre_ratio = dataParams[18]
        pxDegree = (funcs.convertPixelToArcangle(
            posx, distanceToMonitor, pixel_metre_ratio))*0.16
        condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        conditionVALUE = condition_dictionary[1]
        kwargs = {
            'frequency': conditionVALUE[0], 'position': conditionVALUE[1]}
        fs = float(kwargs['frequency'])
        frame_number = dataParams[len(dataParams)-1]
        probe_contrast = p.diff_bkg
        bkg_contrast = dataParams[12]
        frame_number += 1
        cL_flick = flicker_update(self, frame_number, probe_contrast,
                                  bkg_contrast, flicker_freq=fs, monitor_refresh_rate=60)
        # params.color = (cL_flick, cL_flick, cL_flick, 1.0)
        dataParams[len(dataParams)-1] = frame_number
        to_Text(self.fileParams,       dataParams)

        x, y = self.pos
        w2 = self.w/2.0
        glUseProgram(self.program)
        glPushMatrix()
        glLoadIdentity()
        # <- added; updates argument in shader code.
        glUniform1f(self.uniforms['diff_bkg'], cL_flick)
        glUniform1f(self.uniforms['a'], pxDegree)
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)

# =============================================================================
#
# =============================================================================


class two_SOA_frequency_phase(stim(th=0.0, R=50.0, d=3.0, alpha=1.0, a=10.0, b=10.0, width=0.5, bkg=0.0, diff_bkg_1=0.018, diff_bkg_2=0.018,
                                   center_x=0.0, center_y=0.0, ppd_x=76.6, ppd_y=71.9, fs1=0.5, fs2=0.5)):
    """Orientation circle stimulus
    
    :param th: size of stimulus
    :param R: radius
    :param d: width of orientation bar
    :param width: width of ellipse
    :param diff_bkg: difference added to background contrast
    """
    frag_source = """
    uniform float th, sigma, gap, alpha, a, b, width, bkg, diff_bkg_1,diff_bkg_2, center_x, center_y, ppd_x, ppd_y;
    float edge = 40.0;

    float lined(float t, float x, float y) {
        return abs(-sin(t)*x+cos(t)*y);
    }

    float g(float x, float s2, float e2) {
        return exp(-0.5*pow(abs(x)/s2,e2));
    }
    
    void main( void ) {
        //float x = gl_TexCoord[0].x - 0.5;
        //float y = -(gl_TexCoord[0].y - 0.5);
        
        float x = gl_FragCoord.x; // — Screen Pixel Coordinates
        float y = gl_FragCoord.y; // — Screen Pixel Coordinates

        // Convert texture coordinates to screen pixel coordinates directly
        float x_px = x; // 0 to screen_width_pixels
        float y_px = y; // 0 to screen_height_pixels

        // Convert to degrees of visual angle
        float x_deg = (x_px - center_x) / ppd_x;
        float y_deg = (y_px - center_y) / ppd_y;
        
 
        // Compute the square equation
        // Parameters to position bars at ±offset
        float bar_offset = a;  // Distance from center to each bar
        float half_width = width / 2.0;
        
        //bool in_right_bar = (x_deg >= bar_offset - half_width) && (x_deg <= bar_offset + half_width);
        //bool in_left_bar  = (x_deg >= -bar_offset - half_width) && (x_deg <= -bar_offset + half_width);
        //bool in_bar = (in_right_bar || in_left_bar);
        
        bool in_left_bar  = (x_deg >= -bar_offset - width) && (x_deg <= -bar_offset);
        bool in_right_bar = (x_deg >= bar_offset) && (x_deg <= bar_offset + width);
        
        // Check vertical bounds
        bool in_height = (y_deg <= b) && (y_deg >= -b);
        
        //float c = (in_bar && in_height) ? diff_bkg : bkg; 
        
        float c = bkg;
        if (in_left_bar && in_height) {
            c = diff_bkg_1;
        } else if (in_right_bar && in_height) {
            c = diff_bkg_2;
        } else {
            c = bkg;
        }
        gl_FragColor = vec4( c,c,c,alpha );
        }
    """

    def __init__(self, pos, posCentre, fileParams, fileADM_cond, filePosition, params=Params()):
        import Functions.functionUSE as funcs
        import time
        self.start_specfic_t = time.perf_counter()
        self.time_stamp = 0.0
        self.frame_number = 0.0
        self.pos = pos
        self.posCentre = posCentre
        self.fileParams = fileParams
        self.filePosition = filePosition
        self.fileADM_cond = fileADM_cond
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms       = dict(map(self.shader.uniform, ['th', 'sigma', 'gap', 'alpha', 'a', 'b', 'width', 'bkg', 'diff_bkg_1','diff_bkg_2',
                                                             'center_x', 'center_y', 'ppd_x', 'ppd_y']))
        self.dataParams = from_Text(self.fileParams)
        self.dataPosition = from_Text(self.filePosition)
        self.condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        glUseProgram(self.program)
        self.w = p.R*2.5
        glUniform1f(self.uniforms['th'], p.th)
        glUniform1f(self.uniforms['sigma'], 0.4)  # 0.4
        glUniform1f(self.uniforms['gap'], p.d/self.w)
        glUniform1f(self.uniforms['alpha'], p.alpha)
        glUniform1f(self.uniforms['a'], p.a)
        glUniform1f(self.uniforms['b'], p.b)
        glUniform1f(self.uniforms['center_x'], self.pos[0])
        glUniform1f(self.uniforms['center_y'], self.pos[1])
        glUniform1f(self.uniforms['ppd_x'], p.ppd_x)
        glUniform1f(self.uniforms['ppd_y'], p.ppd_y)
        glUniform1f(self.uniforms['width'], p.width)
        glUniform1f(self.uniforms['bkg'], p.bkg)
        glUniform1f(self.uniforms['diff_bkg_1'], p.diff_bkg_1)
        glUniform1f(self.uniforms['diff_bkg_2'], p.diff_bkg_2)
        glUseProgram(0)

    def draw(self):
        import time
        import Functions.functionUSE as funcs
        self.condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        conditionVALUE = self.condition_dictionary[1]
        kwargs = {'frequency': conditionVALUE[0], 'position': conditionVALUE[1], 'general': conditionVALUE[2]}
        condition_frame = float(kwargs['general'])
        self.dataParams = from_Text(self.fileParams)
        p = self.params
        distanceToMonitor = self.dataParams[17]
        pixel_metre_ratio = self.dataParams[18]
        end_time = time.perf_counter()
        # start_timer             = self.dataParams[33]
        self.frame_number = self.dataParams[len(self.dataParams)-1]
        # elapsed                 = end_time - self.start_specfic_t
        time_index = float(self.frame_number / 60.0)
        stimulus_amplitude = 0.0  # p.diff_bkg
        bkg_contrast = self.dataParams[12]
        monitor_refresh_rate = self.dataParams[31]
        # if self.frame_number <= 0:
        #     self.time_stamp = elapsed
        # else:
        #     pass

        fs1, fs2 = p.fs1, p.fs2
        phase_degree1, phase_degree2 = p.phase_degree1, p.phase_degree2
        if (int(self.frame_number) == int(30)):
            print('Stimulus --- gs --- ', condition_frame,
                  ' --- frame --- ', int(self.frame_number))
            # time_sec                = elapsed-self.time_stamp
            cL_flick_1 = flicker_update_smooth(
                self, stimulus_amplitude, bkg_contrast, flicker_freq=fs1, time_sec=0, phasedegree=phase_degree1)
            cL_flick_2 = flicker_update_smooth(
                self, stimulus_amplitude, bkg_contrast, flicker_freq=fs2, time_sec=0, phasedegree=phase_degree2)

        else:
            cL_flick_1 = bkg_contrast
            cL_flick_2 = bkg_contrast
            pass

        self.frame_number += 1
        self.dataParams[len(self.dataParams)-1] = self.frame_number
        to_Text(self.fileParams,       self.dataParams)
        x, y = self.pos
        w2 = self.w/2.0
        glUseProgram(self.program)
        glPushMatrix()
        glLoadIdentity()
        # <- added; updates argument in shader code.
        glUniform1f(self.uniforms['diff_bkg_1'], cL_flick_1)
        # <- added; updates argument in shader code.
        glUniform1f(self.uniforms['diff_bkg_2'], cL_flick_2)
        # glUniform1f(self.uniforms['bkg'],bkgCHG)
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)


class two_flashing_frequency_phase(stim(th=0.0, R=50.0, d=3.0, alpha=1.0, a=10.0, b=10.0, width=0.5, bkg=0.0, diff_bkg_1=0.018, diff_bkg_2=0.018,
                                        center_x=0.0, center_y=0.0, ppd_x=76.6, ppd_y=71.9, fs1=0.5, fs2=0.5, amplitude=1.0)):
    """Orientation circle stimulus
    
    :param th: size of stimulus
    :param R: radius
    :param d: width of orientation bar
    :param width: width of ellipse
    :param diff_bkg: difference added to background contrast
    """
    frag_source = """
    uniform float th, sigma, gap, alpha, a, b, width, bkg, diff_bkg_1,diff_bkg_2, center_x, center_y, ppd_x, ppd_y;
    float edge = 40.0;

    float lined(float t, float x, float y) {
        return abs(-sin(t)*x+cos(t)*y);
    }

    float g(float x, float s2, float e2) {
        return exp(-0.5*pow(abs(x)/s2,e2));
    }
    
    void main( void ) {
        //float x = gl_TexCoord[0].x - 0.5;
        //float y = -(gl_TexCoord[0].y - 0.5);
        
        float x = gl_FragCoord.x; // — Screen Pixel Coordinates
        float y = gl_FragCoord.y; // — Screen Pixel Coordinates

        // Convert texture coordinates to screen pixel coordinates directly
        float x_px = x; // 0 to screen_width_pixels
        float y_px = y; // 0 to screen_height_pixels

        // Convert to degrees of visual angle
        float x_deg = (x_px - center_x) / ppd_x;
        float y_deg = (y_px - center_y) / ppd_y;
        
 
        // Compute the square equation
        // Parameters to position bars at ±offset
        float bar_offset = a;  // Distance from center to each bar
        float half_width = width / 2.0;
        
        bool in_right_bar = (x_deg >= bar_offset - half_width) && (x_deg <= bar_offset + half_width);
        bool in_left_bar  = (x_deg >= -bar_offset - half_width) && (x_deg <= -bar_offset + half_width);
        //bool in_bar = (in_right_bar || in_left_bar);
        
        //bool in_left_bar  = (x_deg >= -bar_offset - width) && (x_deg <= -bar_offset);
        //bool in_right_bar = (x_deg >= bar_offset) && (x_deg <= bar_offset + width);
        
        // Check vertical bounds
        bool in_height = (y_deg <= b) && (y_deg >= -b);
        
        //float c = (in_bar && in_height) ? diff_bkg : bkg; 
        
        float c = bkg;
        if (in_left_bar && in_height) {
            c = diff_bkg_1;
        } else if (in_right_bar && in_height) {
            c = diff_bkg_2;
        } else {
            c = bkg;
        }
        gl_FragColor = vec4( c,c,c,alpha );
        }
    """

    def __init__(self, pos, posCentre, fileParams, fileADM_cond, filePosition, params=Params()):
        import Functions.functionUSE as funcs
        import time
        self.start_specfic_t = time.perf_counter()
        self.time_stamp = 0.0
        self.frame_number = 0.0
        self.pos = pos
        self.posCentre = posCentre
        self.fileParams = fileParams
        self.filePosition = filePosition
        self.fileADM_cond = fileADM_cond
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms       = dict(map(self.shader.uniform, ['th', 'sigma', 'gap', 'alpha', 'a', 'b', 'width', 'bkg', 'diff_bkg_1','diff_bkg_2',
                                                             'center_x', 'center_y', 'ppd_x', 'ppd_y']))
        self.dataParams = from_Text(self.fileParams)
        self.dataPosition = from_Text(self.filePosition)
        self.condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        glUseProgram(self.program)
        self.w = p.R*2.5
        glUniform1f(self.uniforms['th'], p.th)
        glUniform1f(self.uniforms['sigma'], 0.4)  # 0.4
        glUniform1f(self.uniforms['gap'], p.d/self.w)
        glUniform1f(self.uniforms['alpha'], p.alpha)
        glUniform1f(self.uniforms['a'], p.a)
        glUniform1f(self.uniforms['b'], p.b)
        glUniform1f(self.uniforms['center_x'], self.pos[0])
        glUniform1f(self.uniforms['center_y'], self.pos[1])
        glUniform1f(self.uniforms['ppd_x'], p.ppd_x)
        glUniform1f(self.uniforms['ppd_y'], p.ppd_y)
        glUniform1f(self.uniforms['width'], p.width)
        glUniform1f(self.uniforms['bkg'], p.bkg)
        glUniform1f(self.uniforms['diff_bkg_1'], p.diff_bkg_1)
        glUniform1f(self.uniforms['diff_bkg_2'], p.diff_bkg_2)
        glUseProgram(0)

    def draw(self):
        import time
        import Functions.functionUSE as funcs
        self.condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        conditionVALUE = self.condition_dictionary[1]
        kwargs = {'frequency': conditionVALUE[0], 'position': conditionVALUE[1], 'general': conditionVALUE[2]}
        condition_frame = float(kwargs['general'])
        self.dataParams = from_Text(self.fileParams)
        p = self.params
        distanceToMonitor = self.dataParams[17]
        pixel_metre_ratio = self.dataParams[18]
        end_time = time.perf_counter()
        # start_timer             = self.dataParams[33]
        self.frame_number = self.dataParams[len(self.dataParams)-1]
        # elapsed                 = end_time - self.start_specfic_t
        time_index = float(self.frame_number / 60.0)
        stimulus_amplitude = float(p.amplitude)  # 0.0 # p.diff_bkg
        bkg_contrast = self.dataParams[12]
        monitor_refresh_rate = self.dataParams[31]
        # if self.frame_number <= 0:
        #     self.time_stamp = elapsed
        # else:
        #     pass

        fs1, fs2 = p.fs1, p.fs2
        phase_degree1, phase_degree2 = p.phase_degree1, p.phase_degree2

        # print('Stimulus --- gs --- ', condition_frame, ' --- frame --- ', int(self.frame_number))
        # time_sec                = elapsed-self.time_stamp
        cL_flick_1 = flicker_update_smooth_bkgUP(
            self, stimulus_amplitude, bkg_contrast, flicker_freq=fs1, time_sec=time_index, phasedegree=phase_degree1)
        cL_flick_2 = flicker_update_smooth_bkgUP(
            self, stimulus_amplitude, bkg_contrast, flicker_freq=fs2, time_sec=time_index, phasedegree=phase_degree2)

        self.frame_number += 1

        if self.frame_number == 121:  # 61:#
            self.frame_number = 0
        else:
            pass

        self.dataParams[len(self.dataParams)-1] = self.frame_number
        to_Text(self.fileParams,       self.dataParams)
        x, y = self.pos
        w2 = self.w/2.0
        glUseProgram(self.program)
        glPushMatrix()
        glLoadIdentity()
        # <- added; updates argument in shader code.
        glUniform1f(self.uniforms['diff_bkg_1'], cL_flick_1)
        # <- added; updates argument in shader code.
        glUniform1f(self.uniforms['diff_bkg_2'], cL_flick_2)
        # glUniform1f(self.uniforms['bkg'],bkgCHG)
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)


class drifiting_grating(stim(th=0.0, R=1000.0, d=5.0, alpha=1.0, a=10.0, b=10.0, width=0.5, bkg=0.0, diff_bkg_1=0.018, diff_bkg_2=0.018,
                             center_x=0.0, center_y=0.0, ppd_x=76.6, ppd_y=71.9, fs1=0.5, fs2=0.5, fx=2.0, pi=0.341,
                             phase1=0.0, phase2=0.0, amplitude=1.0)):
    """Orientation circle stimulus
    
    :param th: size of stimulus
    :param R: radius
    :param d: width of orientation bar
    :param width: width of ellipse
    :param diff_bkg: difference added to background contrast
    """
    frag_source = """
    uniform float th, sigma, gap, alpha, a, b, width, bkg, diff_bkg_1,diff_bkg_2, center_x, center_y, ppd_x, ppd_y, fs1, fs2, fx, pi, t, phase1, phase2,amplitude;
    float edge = 40.0;

    float lined(float t, float x, float y) {
        return abs(-sin(t)*x+cos(t)*y);
    }

    float g(float x, float s2, float e2) {
        return exp(-0.5*pow(abs(x)/s2,e2));
    }
    
    void main( void ) {
        //float x = gl_TexCoord[0].x - 0.5;
        //float y = -(gl_TexCoord[0].y - 0.5);
        
        float x = gl_FragCoord.x; // — Screen Pixel Coordinates
        float y = gl_FragCoord.y; // — Screen Pixel Coordinates

        // Convert texture coordinates to screen pixel coordinates directly
        float x_px = x; // 0 to screen_width_pixels
        float y_px = y; // 0 to screen_height_pixels

        // Convert to degrees of visual angle
        float x_deg = (x_px - center_x) / ppd_x;
        float y_deg = (y_px - center_y) / ppd_y;
        
 
        // Compute the square equation
        // Parameters to position bars at ±offset
        float bar_offset = a;  // Distance from center to each bar
        float half_width = width / 2.0;
        
        bool in_right_bar = (x_deg >= bar_offset - half_width) && (x_deg <= bar_offset + half_width);
        bool in_left_bar  = (x_deg >= -bar_offset - half_width) && (x_deg <= -bar_offset + half_width);

        
        // Check vertical bounds
        bool in_height = (y_deg <= b/2) && (y_deg >= -b/2);
        
        float v1 = fs1/fx;
        float v2 = fs2/fx;
        
        float c1 = amplitude*sin(2.0*pi*fx*(x_deg-(0.0)-v1*t) + phase1);
        float c2 = amplitude*sin(2.0*pi*fx*(x_deg+(0.0)+v2*t) + phase2);

        float c = bkg;
        if (in_left_bar && in_height) {
            c = bkg+c1*bkg;
        } else if (in_right_bar && in_height) {
            c = bkg+c2*bkg;
        } else {
            c = bkg;
        }
        gl_FragColor = vec4( c,c,c,alpha );
        }
    """

    def __init__(self, pos, posCentre, fileParams, fileADM_cond, filePosition, params=Params()):
        import Functions.functionUSE as funcs
        import time
        self.start_specfic_t = time.perf_counter()
        self.time_stamp = 0.0
        self.frame_number = 0.0
        self.pos = pos
        self.posCentre = posCentre
        self.fileParams = fileParams
        self.filePosition = filePosition
        self.fileADM_cond = fileADM_cond
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms       = dict(map(self.shader.uniform, ['th', 'sigma', 'gap', 'alpha', 'a', 'b', 'width', 'bkg', 'diff_bkg_1','diff_bkg_2',
                                                             'center_x', 'center_y', 'ppd_x', 'ppd_y', 'fx', 'pi', 't', 'phase1', 'phase2',
                                                             'fs1', 'fs2', 'amplitude']))
        self.dataParams = from_Text(self.fileParams)
        self.dataPosition = from_Text(self.filePosition)
        self.condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        glUseProgram(self.program)
        self.w = p.R*2.5
        glUniform1f(self.uniforms['th'], p.th)
        glUniform1f(self.uniforms['sigma'], 0.4)  # 0.4
        glUniform1f(self.uniforms['gap'], p.d/self.w)
        glUniform1f(self.uniforms['alpha'], p.alpha)
        glUniform1f(self.uniforms['a'], p.a)
        glUniform1f(self.uniforms['b'], p.b)
        glUniform1f(self.uniforms['center_x'], self.pos[0])
        glUniform1f(self.uniforms['center_y'], self.pos[1])
        glUniform1f(self.uniforms['ppd_x'], p.ppd_x)
        glUniform1f(self.uniforms['ppd_y'], p.ppd_y)
        glUniform1f(self.uniforms['width'], p.width)
        glUniform1f(self.uniforms['bkg'], p.bkg)
        glUniform1f(self.uniforms['diff_bkg_1'], p.diff_bkg_1)
        glUniform1f(self.uniforms['diff_bkg_2'], p.diff_bkg_2)
        glUniform1f(self.uniforms['fx'], p.fx)
        glUniform1f(self.uniforms['fs1'], p.fs1)
        glUniform1f(self.uniforms['fs2'], p.fs2)
        glUniform1f(self.uniforms['pi'], p.pi)
        glUniform1f(self.uniforms['t'], self.time_stamp)
        glUniform1f(self.uniforms['phase1'], p.phase_degree1)
        glUniform1f(self.uniforms['phase2'], p.phase_degree2)
        glUniform1f(self.uniforms['amplitude'], p.amplitude)
        glUseProgram(0)

    def draw(self):
        import time
        import Functions.functionUSE as funcs
        self.condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        conditionVALUE = self.condition_dictionary[1]
        kwargs = {'frequency': conditionVALUE[0], 'position': conditionVALUE[1], 'general': conditionVALUE[2]}
        condition_frame = float(kwargs['general'])
        self.dataParams = from_Text(self.fileParams)
        p = self.params
        distanceToMonitor = self.dataParams[17]
        pixel_metre_ratio = self.dataParams[18]
        end_time = time.perf_counter()
        # start_timer             = self.dataParams[33]
        self.frame_number = self.dataParams[len(self.dataParams)-1]
        # elapsed                 = end_time - self.start_specfic_t
        time_index = float(self.frame_number / 60.0)
        stimulus_amplitude = 0.0  # p.diff_bkg
        bkg_contrast = self.dataParams[12]
        monitor_refresh_rate = self.dataParams[31]
        # if self.frame_number <= 0:
        #     self.time_stamp = elapsed
        # else:
        #     pass

        fs1, fs2 = p.fs1, p.fs2
        phase_degree1, phase_degree2 = p.phase_degree1, p.phase_degree2

        # print('Stimulus --- gs --- ', condition_frame, ' --- frame --- ', int(self.frame_number))
        # time_sec                = elapsed-self.time_stamp
        # cL_flick_1              = flicker_update_smooth(self, stimulus_amplitude, bkg_contrast, flicker_freq=fs1, time_sec=time_index, phasedegree=phase_degree1)
        # cL_flick_2              = flicker_update_smooth(self, stimulus_amplitude, bkg_contrast, flicker_freq=fs2, time_sec=time_index, phasedegree=phase_degree2)

        self.frame_number += 1

        if self.frame_number == 121:  # 61:#
            self.frame_number = 0
        else:
            pass

        self.dataParams[len(self.dataParams)-1] = self.frame_number
        to_Text(self.fileParams,       self.dataParams)
        x, y = self.pos
        w2 = self.w  # /2.0
        glUseProgram(self.program)
        glPushMatrix()
        glLoadIdentity()
        # glUniform1f(self.uniforms['diff_bkg_1'],cL_flick_1) # <- added; updates argument in shader code.
        # glUniform1f(self.uniforms['diff_bkg_2'],cL_flick_2) # <- added; updates argument in shader code.
        glUniform1f(self.uniforms['t'], time_index)
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)  # all 10s were 1s
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)


class two_lines_displacement_baseFind(stim(th=0.0, R=50.0, d=3.0, alpha=1.0, a=10.0, b=10.0, width=0.5, bkg=0.0, diff_bkg_1=0.018, diff_bkg_2=0.018,
                                           center_x=0.0, center_y=0.0, ppd_x=76.6, ppd_y=71.9, fs1=0.5, fs2=0.5, frameNumber=28)):
    """Orientation circle stimulus
    
    :param th: size of stimulus
    :param R: radius
    :param d: width of orientation bar
    :param width: width of ellipse
    :param diff_bkg: difference added to background contrast
    """
    frag_source = """
    uniform float th, sigma, gap, alpha, a, b, width, bkg, diff_bkg_1,diff_bkg_2, center_x, center_y, ppd_x, ppd_y;
    float edge = 40.0;

    float lined(float t, float x, float y) {
        return abs(-sin(t)*x+cos(t)*y);
    }

    float g(float x, float s2, float e2) {
        return exp(-0.5*pow(abs(x)/s2,e2));
    }
    
    void main( void ) {
        //float x = gl_TexCoord[0].x - 0.5;
        //float y = -(gl_TexCoord[0].y - 0.5);
        
        float x = gl_FragCoord.x; // — Screen Pixel Coordinates
        float y = gl_FragCoord.y; // — Screen Pixel Coordinates

        // Convert texture coordinates to screen pixel coordinates directly
        float x_px = x; // 0 to screen_width_pixels
        float y_px = y; // 0 to screen_height_pixels

        // Convert to degrees of visual angle
        float x_deg = (x_px - center_x) / ppd_x;
        float y_deg = (y_px - center_y) / ppd_y;
        
 
        // Compute the square equation
        // Parameters to position bars at ±offset
        float bar_offset = a;  // Distance from center to each bar
        float half_width = width / 2.0;
        
        bool in_right_bar = (x_deg >= bar_offset - half_width) && (x_deg <= bar_offset + half_width);
        bool in_left_bar  = (x_deg >= -bar_offset - half_width) && (x_deg <= -bar_offset + half_width);
        //bool in_bar = (in_right_bar || in_left_bar);
        
        //bool in_left_bar  = (x_deg >= -bar_offset - width) && (x_deg <= -bar_offset);
        //bool in_right_bar = (x_deg >= bar_offset) && (x_deg <= bar_offset + width);
        
        // Check vertical bounds
        bool in_height = (y_deg <= b) && (y_deg >= -b);
        
        //float c = (in_bar && in_height) ? diff_bkg : bkg; 
        
        float c = bkg;
        if (in_left_bar && in_height) {
            c = diff_bkg_1;
        } else if (in_right_bar && in_height) {
            c = diff_bkg_2;
        } else {
            c = bkg;
        }
        gl_FragColor = vec4( c,c,c,alpha );
        }
    """

    def __init__(self, pos, posCentre, fileParams, fileADM_cond, filePosition, params=Params()):
        import Functions.functionUSE as funcs
        import time
        self.start_specfic_t = time.perf_counter()
        self.time_stamp = 0.0
        self.frame_number = 0.0
        self.pos = pos
        self.posCentre = posCentre
        self.fileParams = fileParams
        self.filePosition = filePosition
        self.fileADM_cond = fileADM_cond
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms       = dict(map(self.shader.uniform, ['th', 'sigma', 'gap', 'alpha', 'a', 'b', 'width', 'bkg', 'diff_bkg_1','diff_bkg_2',
                                                             'center_x', 'center_y', 'ppd_x', 'ppd_y']))
        self.dataParams = from_Text(self.fileParams)
        self.dataPosition = from_Text(self.filePosition)
        self.condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        glUseProgram(self.program)
        self.w = p.R*2.5
        glUniform1f(self.uniforms['th'], p.th)
        glUniform1f(self.uniforms['sigma'], 0.4)  # 0.4
        glUniform1f(self.uniforms['gap'], p.d/self.w)
        glUniform1f(self.uniforms['alpha'], p.alpha)
        glUniform1f(self.uniforms['a'], p.a)
        glUniform1f(self.uniforms['b'], p.b)
        glUniform1f(self.uniforms['center_x'], self.pos[0])
        glUniform1f(self.uniforms['center_y'], self.pos[1])
        glUniform1f(self.uniforms['ppd_x'], p.ppd_x)
        glUniform1f(self.uniforms['ppd_y'], p.ppd_y)
        glUniform1f(self.uniforms['width'], p.width)
        glUniform1f(self.uniforms['bkg'], p.bkg)
        glUniform1f(self.uniforms['diff_bkg_1'], p.diff_bkg_1)
        glUniform1f(self.uniforms['diff_bkg_2'], p.diff_bkg_2)
        glUseProgram(0)

    def draw(self):
        import time
        import Functions.functionUSE as funcs

        self.condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        conditionVALUE = self.condition_dictionary[1]
        kwargs = {'frequency': conditionVALUE[0], 'position': conditionVALUE[1], 'general': conditionVALUE[2]}
        condition_frame = float(kwargs['general'])
        self.dataParams = from_Text(self.fileParams)
        p = self.params
        distanceToMonitor = self.dataParams[17]
        pixel_metre_ratio = self.dataParams[18]
        end_time = time.perf_counter()
        # start_timer             = self.dataParams[33]
        self.frame_number = self.dataParams[len(self.dataParams)-1]
        # elapsed                 = end_time - self.start_specfic_t
        # time_index              = float(self.frame_number / 60.0)
        frameNumber = p.frameNumber
        # want close to inflection point
        time_index = float(frameNumber / 60.0)

        stimulus_amplitude = 0.0  # p.diff_bkg
        bkg_contrast = self.dataParams[12]
        monitor_refresh_rate = self.dataParams[31]
        # if self.frame_number <= 0:
        #     self.time_stamp = elapsed
        # else:
        #     pass
        self.dataPosition = from_Text(self.filePosition)
        posx = (self.dataPosition[0])
        pxDegree = (funcs.convertPixelToArcangle(
            posx, distanceToMonitor, pixel_metre_ratio))

        fs1, fs2 = p.fs1, p.fs2
        phase_degree1, phase_degree2 = p.phase_degree1, p.phase_degree2

        # print('Stimulus --- gs --- ', condition_frame, ' --- frame --- ', int(self.frame_number))
        # time_sec                = elapsed-self.time_stamp
        cL_flick_1 = flicker_update_smooth(
            self, stimulus_amplitude, bkg_contrast, flicker_freq=fs1, time_sec=time_index, phasedegree=phase_degree1)
        cL_flick_2 = flicker_update_smooth(
            self, stimulus_amplitude, bkg_contrast, flicker_freq=fs2, time_sec=time_index, phasedegree=phase_degree2)

        self.frame_number += 1

        if self.frame_number == 121:  # 61:#
            self.frame_number = 0
        else:
            pass

        self.dataParams[len(self.dataParams)-1] = self.frame_number
        to_Text(self.fileParams,       self.dataParams)
        x, y = self.pos
        w2 = self.w/2.0
        glUseProgram(self.program)
        glPushMatrix()
        glLoadIdentity()
        # <- added; updates argument in shader code.
        glUniform1f(self.uniforms['diff_bkg_1'], cL_flick_1)
        # <- added; updates argument in shader code.
        glUniform1f(self.uniforms['diff_bkg_2'], cL_flick_2)
        glUniform1f(self.uniforms['a'], pxDegree)
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)


class Line_condition_phaseFrame(stim(length=100.0, width=10.0, angle=0.0, color=(1.0, 1.0, 1.0, 1.0))):
    def __init__(self, posCentre, pos, admTEXT, fileParamsMain, fileParams, fileParamsPosition, filesDataMain, fileADM_cond, params=Params()):
        import time
        self.last_time = time.time()
        self.start_specfic_t = time.perf_counter()
        self.frame_number = 0.0
        self.checkZero = 0.0
        self.time_stamp = 0.0
        self.previous_time = 0.0
        self.frame_times = []
        self.pos = pos
        self.posCentre = posCentre
        self.NAN = admTEXT
        self.fileParams = fileParams
        self.filesDataMain = filesDataMain
        self.params = copy_params(self._defaults, params)
        self.filePosition = fileParamsPosition
        self.fileParamsMain = fileParamsMain
        self.fileADM_cond = fileADM_cond
        self.dataParams = from_Text(self.fileParams)
        self.dataPosition = from_Text(self.filePosition)
        self.dataParamsMain = from_Text(self.fileParamsMain)

    def draw(self):
        import time
        import Functions.functionUSE as funcs
        self.dataParams = from_Text(self.fileParams)
        self.condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        p = self.params
        distanceToMonitor = self.dataParams[17]
        pixel_metre_ratio = self.dataParams[18]
        conditionVALUE = self.condition_dictionary[1]
        kwargs = {'frequency': conditionVALUE[0], 'position': conditionVALUE[1], 'general': conditionVALUE[2]}
        condition_phase = float(kwargs['general'])
        # condition_frame         = float(kwargs['frequency'])

        # =====================================================================
        self.px = self.pos[0]
        self.py = self.pos[1]
        self.dataParams = from_Text(self.fileParams)
        self.dataParamsMain = from_Text(self.fileParamsMain)
        # =====================================================================
        # end_time                = time.perf_counter()
        # self.frame_times.append(end_time)
        # start_timer             = self.dataParams[33]
        self.frame_number = self.dataParams[len(self.dataParams)-1]
        # elapsed                 = end_time - self.start_specfic_t #  start_timer #
        monitor_refresh_rate = self.dataParams[31]
        # now                     = time.time()
        # frame_interval          = now - self.last_time
        time_index = float(self.frame_number / 60.0)

        # if self.frame_number <= 0:
        #     self.time_stamp = elapsed
        # elif self.frame_number >= 120:
        #     fps             = round(1.0 /frame_interval,3)
        #     intervals       = [t2 - t1 for t1, t2 in zip(self.frame_times[:-1], self.frame_times[1:])]
        #     avg_interval    = sum(intervals) / len(intervals)
        #     true_fps        = 1.0 / avg_interval
        #     print(f"True screen FPS: {true_fps:.2f}")
        #     print("Actual FPS:",  fps, "  Time index: ", round(time_index,3),
        #           "  Frame number: ", self.frame_number, 'time:', round(elapsed-self.time_stamp,3), 'dt:', round(elapsed-self.time_stamp-self.previous_time,3))
        # else:
        #     pass
        # =====================================================================
        # admTEXT # <- needs to be accesed just like position.
        bkg_contrast = self.dataParams[12]
        admTEXT = self.dataParamsMain[0]
        params = self.params
        # time_index          = float(self.frame_number / 60.0)
        fs1, fs2 = p.fs1, p.fs2
        phase_degree1, phase_degree2 = p.phase_degree1, p.phase_degree2
        target_phase = condition_phase

        epsilon = 0.05
        phase = (2*np.pi*fs1*time_index-np.deg2rad(phase_degree1)) % (np.pi*2)
        condition = np.deg2rad(target_phase)
        diff = abs(phase-condition)
        if (diff < epsilon) or (abs(diff-(2*np.pi)) < epsilon):
            if self.checkZero == 0.0:
                cL = funcs.adMethod_luminance_ID(
                    admTEXT, self.fileParams, self.filesDataMain)
                print('Probe --- gs --- ', condition_phase, ' --- frame --- ',
                      int(self.frame_number), ' -- condition --', condition % (np.pi*2))
                self.checkZero += 1
            elif self.checkZero > 0.0:
                cL = bkg_contrast
        else:
            cL = bkg_contrast

        params.color = (cL, cL, cL, 1.0)
        self.pos = [self.px, self.py]
        # self.frame_number  +=1
        # self.last_time      = now
        # self.previous_time  = elapsed-self.time_stamp
        """
        probe needs to record the frame number.
        """
        # frame_number    = dataParams[len(dataParams)-1]
        # Time (in seconds) for the current frame
        # t = frame_number / monitor_refresh_rate
        # dataParams[len(dataParams)-2] = t
        # to_Text(self.fileParams, dataParams)
        """
        Then save to a file for posX and posY only, which can be accesed by "ADM trial".
        """
        if hasattr(params, 'color') and not iterable(params.color):
            params.color = [params.color]*3
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.length, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.params.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()


class Line_condition_timeFrame(stim(length=100.0, width=10.0, angle=0.0, color=(1.0, 1.0, 1.0, 1.0))):
    def __init__(self, posCentre, pos, admTEXT, fileParamsMain, fileParams, fileParamsPosition, filesDataMain, fileADM_cond, params=Params()):
        import time
        self.last_time = time.time()
        self.start_specfic_t = time.perf_counter()
        self.frame_number = 0.0
        self.checkZero = 0.0
        self.time_stamp = 0.0
        self.previous_time = 0.0
        self.frame_times = []
        self.pos = pos
        self.posCentre = posCentre
        self.NAN = admTEXT
        self.fileParams = fileParams
        self.filesDataMain = filesDataMain
        self.params = copy_params(self._defaults, params)
        self.filePosition = fileParamsPosition
        self.fileParamsMain = fileParamsMain
        self.fileADM_cond = fileADM_cond
        self.dataParams = from_Text(self.fileParams)
        self.dataPosition = from_Text(self.filePosition)
        self.dataParamsMain = from_Text(self.fileParamsMain)

    def draw(self):
        import time
        import Functions.functionUSE as funcs
        self.dataParams = from_Text(self.fileParams)
        self.condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        p = self.params
        distanceToMonitor = self.dataParams[17]
        pixel_metre_ratio = self.dataParams[18]
        conditionVALUE = self.condition_dictionary[1]
        kwargs = {'frequency': conditionVALUE[0], 'position': conditionVALUE[1], 'general': conditionVALUE[2]}
        condition_frame = float(kwargs['general'])
        # condition_frame         = float(kwargs['frequency'])

        # =====================================================================
        self.px = self.pos[0]
        self.py = self.pos[1]
        self.dataParams = from_Text(self.fileParams)
        self.dataParamsMain = from_Text(self.fileParamsMain)
        # =====================================================================
        # end_time                = time.perf_counter()
        # self.frame_times.append(end_time)
        # start_timer             = self.dataParams[33]
        self.frame_number = self.dataParams[len(self.dataParams)-1]
        # elapsed                 = end_time - self.start_specfic_t #  start_timer #
        monitor_refresh_rate = self.dataParams[31]
        # now                     = time.time()
        # frame_interval          = now - self.last_time
        time_index = float(self.frame_number / 60.0)

        # if self.frame_number <= 0:
        #     self.time_stamp = elapsed
        # elif self.frame_number >= 120:
        #     fps             = round(1.0 /frame_interval,3)
        #     intervals       = [t2 - t1 for t1, t2 in zip(self.frame_times[:-1], self.frame_times[1:])]
        #     avg_interval    = sum(intervals) / len(intervals)
        #     true_fps        = 1.0 / avg_interval
        #     print(f"True screen FPS: {true_fps:.2f}")
        #     print("Actual FPS:",  fps, "  Time index: ", round(time_index,3),
        #           "  Frame number: ", self.frame_number, 'time:', round(elapsed-self.time_stamp,3), 'dt:', round(elapsed-self.time_stamp-self.previous_time,3))
        # else:
        #     pass
        # =====================================================================
        # admTEXT # <- needs to be accesed just like position.
        bkg_contrast = self.dataParams[12]
        admTEXT = self.dataParamsMain[0]
        params = self.params
        # time_index          = float(self.frame_number / 60.0)

        if int(self.frame_number) == int(condition_frame):
            if self.checkZero == 0.0:
                cL = funcs.adMethod_luminance_ID(
                    admTEXT, self.fileParams, self.filesDataMain)
                print('Probe --- gs --- ', condition_frame,
                      ' --- frame --- ', int(self.frame_number))
                self.checkZero += 1
            elif self.checkZero > 0.0:
                cL = bkg_contrast
        else:
            cL = bkg_contrast

        params.color = (cL, cL, cL, 1.0)
        self.pos = [self.px, self.py]
        # self.frame_number  +=1
        # self.last_time      = now
        # self.previous_time  = elapsed-self.time_stamp
        """
        probe needs to record the frame number.
        """
        # frame_number    = dataParams[len(dataParams)-1]
        # Time (in seconds) for the current frame
        # t = frame_number / monitor_refresh_rate
        # dataParams[len(dataParams)-2] = t
        # to_Text(self.fileParams, dataParams)
        """
        Then save to a file for posX and posY only, which can be accesed by "ADM trial".
        """
        if hasattr(params, 'color') and not iterable(params.color):
            params.color = [params.color]*3
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.length, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.params.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()

# =============================================================================
#
# =============================================================================


class Line_ADM_phase(stim(length=100.0, width=10.0, angle=0.0, color=(1.0, 1.0, 1.0, 1.0))):
    def __init__(self, posCentre, pos, admTEXT, fileParamsMain, fileParams, fileParamsPosition, filesDataMain, params=Params()):
        import time
        self.last_time = time.time()
        self.start_specfic_t = time.perf_counter()
        self.frame_number = 0.0
        self.time_stamp = 0.0
        self.previous_time = 0.0
        self.frame_times = []
        self.pos = pos
        self.posCentre = posCentre
        self.NAN = admTEXT
        self.fileParams = fileParams
        self.filesDataMain = filesDataMain
        self.params = copy_params(self._defaults, params)
        self.filePosition = fileParamsPosition
        self.fileParamsMain = fileParamsMain
        self.dataParams = from_Text(self.fileParams)
        self.dataPosition = from_Text(self.filePosition)
        self.dataParamsMain = from_Text(self.fileParamsMain)

    def draw(self):
        import time
        import Functions.functionUSE as funcs
        self.px = self.pos[0]
        self.py = self.pos[1]
        self.dataParams = from_Text(self.fileParams)
        self.dataParamsMain = from_Text(self.fileParamsMain)
        # =====================================================================
        end_time = time.perf_counter()
        self.frame_times.append(end_time)
        # start_timer             = self.dataParams[33]
        elapsed = end_time - self.start_specfic_t  # start_timer #
        monitor_refresh_rate = self.dataParams[31]
        now = time.time()
        frame_interval = now - self.last_time
        time_index = float(self.frame_number / 60.0)
        if self.frame_number <= 0:
            self.time_stamp = elapsed
        elif self.frame_number >= 120:
            fps = round(1.0 / frame_interval, 3)
            intervals = [t2 - t1 for t1,
                         t2 in zip(self.frame_times[:-1], self.frame_times[1:])]
            avg_interval = sum(intervals) / len(intervals)
            true_fps = 1.0 / avg_interval
            print(f"True screen FPS: {true_fps:.2f}")
            print("Actual FPS:",  fps, "  Time index: ", round(time_index, 3),
                  "  Frame number: ", self.frame_number, 'time:', round(elapsed-self.time_stamp, 3), 'dt:', round(elapsed-self.time_stamp-self.previous_time, 3))
        else:
            pass
        # =====================================================================
        # admTEXT # <- needs to be accesed just liek position.
        bkg_contrast = self.dataParams[12]
        admTEXT = self.dataParamsMain[0]
        params = self.params
        time_index = float(self.frame_number / 60.0)
        if (self.frame_number == 61.0) and (time_index >= 1.0):
            cL = funcs.adMethod_luminance_ID(
                admTEXT, self.fileParams, self.filesDataMain)
        else:
            cL = bkg_contrast
        params.color = (cL, cL, cL, 1.0)
        self.pos = [self.px, self.py]
        self.frame_number += 1
        self.last_time = now
        self.previous_time = elapsed-self.time_stamp
        """
        probe needs to record the frame number.
        """
        # frame_number    = dataParams[len(dataParams)-1]
        # Time (in seconds) for the current frame
        # t = frame_number / monitor_refresh_rate
        # dataParams[len(dataParams)-2] = t
        # to_Text(self.fileParams, dataParams)
        """
        Then save to a file for posX and posY only, which can be accesed by "ADM trial".
        """
        if hasattr(params, 'color') and not iterable(params.color):
            params.color = [params.color]*3
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.length, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.params.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()


class two_lines_phase_probe(stim(th=0.0, R=50.0, d=3.0, alpha=1.0, a=10.0, b=10.0, probe_x=0.0, probe_height=10.0, probe_w=0.01, time_index=0.0,
                                 width=0.5, bkg=0.0, diff_bkg=0.018, probe_contrast=1.0, center_x=0.0, center_y=0.0, ppd_x=76.6, ppd_y=71.9)):
    """two flashing lines with a probe region stimulus
    
    :param th: size of stimulus
    :param R: radius
    :param d: width of orientation bar
    :param width: width of flashing lines
    :param diff_bkg: difference added to background contrast
    :param probe_contrast: contrast of the probe
    :param probe_x: x position of the probe
    :param probe_height: height of the probe
    :param probe_width: width of the probe
    """
    frag_source = """
    uniform float th, sigma, gap, alpha, a, b, width, bkg, diff_bkg, probe_contrast, probe_x, probe_height, probe_w, center_x, center_y, ppd_x, ppd_y, time_index , frame_number;
    float edge = 40.0;

    float lined(float t, float x, float y) {
        return abs(-sin(t)*x+cos(t)*y);
    }

    float g(float x, float s2, float e2) {
        return exp(-0.5*pow(abs(x)/s2,e2));
    }
    
    void main( void ) {
        //float x = gl_TexCoord[0].x - 0.5;
        //float y = -(gl_TexCoord[0].y - 0.5);

        float x = gl_FragCoord.x; // — Screen Pixel Coordinates
        float y = gl_FragCoord.y; // — Screen Pixel Coordinates

        // Convert texture coordinates to screen pixel coordinates directly
        float x_px = x; // 0 to screen_width_pixels
        float y_px = y; // 0 to screen_height_pixels

        // Convert to degrees of visual angle
        float x_deg = (x_px - center_x) / ppd_x;
        float y_deg = (y_px - center_y) / ppd_y;
        
        // Compute the square equation
        // Parameters to position bars at ±offset
        float bar_offset = a;  // Distance from center to each bar
        float half_width = width / 2.0;
        
        bool in_right_bar = (x_deg >= bar_offset - half_width) && (x_deg <= bar_offset + half_width);
        bool in_left_bar  = (x_deg >= -bar_offset - half_width) && (x_deg <= -bar_offset + half_width);
        bool in_bar = (in_right_bar || in_left_bar);

        // Check vertical bounds
        bool in_height = (y_deg <= b) && (y_deg >= -b);

        // now to add probe region
        //float probe_xpos        = probe_x;  // Center of the probe region
        //float probe_height      = probe_height;  // Center of the probe region
        //float probe_half_width  = probe_w-(probe_w*0.3); //2;

        //bool in_probe_region = (x_deg >= probe_xpos - probe_half_width) && (x_deg <= probe_xpos + probe_half_width);
        //bool in_probe_height = (y_deg <= probe_height) && (y_deg >= 0.0);
        //bool in_frame_set    = (frame_number >= 61.0) && (frame_number <= 61.0);
        
        // float c = (in_bar && in_height) ? diff_bkg : bkg; 
        float c = bkg;
        if (in_bar && in_height) {
            c = diff_bkg;
        //} else if (in_probe_region && in_probe_height && time_index >= 1.0 && in_frame_set) {
        //    c = probe_contrast;
        } else {
            c = bkg;
        }
        gl_FragColor = vec4( c,c,c,alpha );
    }
    """

    def __init__(self, pos, posCentre, fileParams, fileADM_cond, filePosition, fileParamsMain, filesDataMain, params=Params()):
        import Functions.functionUSE as funcs
        import time
        self.last_time = time.time()
        self.start_specfic_t = time.perf_counter()
        self.frame_number = 0.0
        self.time_stamp = 0.0
        self.previous_time = 0.0
        self.frame_times = []
        self.pos = pos
        self.posCentre = posCentre
        self.fileParams = fileParams
        self.filesDataMain = filesDataMain
        self.fileParamsMain = fileParamsMain
        self.filePosition = filePosition
        self.fileADM_cond = fileADM_cond
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms       = dict(map(self.shader.uniform, ['th', 'sigma', 'gap', 'alpha', 'a', 'b', 'width',
                                                             'bkg', 'diff_bkg', 'center_x', 'center_y',
                                                             'ppd_x', 'ppd_y', 'time_index', 'frame_number',
                                                             'probe_contrast', 'probe_x', 'probe_height', 'probe_w']))
        self.dataParams = from_Text(self.fileParams)
        self.dataPosition = from_Text(self.filePosition)
        self.dataParamsMain = from_Text(self.fileParamsMain)
        self.condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        glUseProgram(self.program)
        self.w = p.R*2.5
        glUniform1f(self.uniforms['th'], p.th)
        glUniform1f(self.uniforms['sigma'], 0.4)  # 0.4
        glUniform1f(self.uniforms['gap'], p.d/self.w)
        glUniform1f(self.uniforms['alpha'], p.alpha)
        glUniform1f(self.uniforms['a'], p.a)
        glUniform1f(self.uniforms['b'], p.b)
        glUniform1f(self.uniforms['center_x'], self.pos[0])
        glUniform1f(self.uniforms['center_y'], self.pos[1])
        glUniform1f(self.uniforms['ppd_x'], p.ppd_x)
        glUniform1f(self.uniforms['ppd_y'], p.ppd_y)
        glUniform1f(self.uniforms['width'], p.width)
        glUniform1f(self.uniforms['time_index'], p.time_index)
        glUniform1f(self.uniforms['frame_number'], self.frame_number)
        glUniform1f(self.uniforms['bkg'], p.bkg)
        glUniform1f(self.uniforms['diff_bkg'], p.diff_bkg)
        glUniform1f(self.uniforms['probe_contrast'], p.probe_contrast)
        glUniform1f(self.uniforms['probe_x'], p.probe_x)
        glUniform1f(self.uniforms['probe_height'], p.probe_height)
        glUniform1f(self.uniforms['probe_w'], p.probe_w)
        glUseProgram(0)

    def draw(self):
        import Functions.functionUSE as funcs
        self.dataParams = from_Text(self.fileParams)
        self.dataPosition = from_Text(self.filePosition)
        self.dataParamsMain = from_Text(self.fileParamsMain)
        self.condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        end_time = time.perf_counter()
        self.frame_times.append(end_time)
        # start_timer             = self.dataParams[33]
        elapsed = end_time - self.start_specfic_t  # start_timer #
        # monitor_refresh_rate    = self.dataParams[31]
        now = time.time()
        frame_interval = now - self.last_time
        time_index = float(self.frame_number / 60.0)
        if self.frame_number <= 0:
            self.time_stamp = elapsed
        elif self.frame_number >= 120:
            fps = round(1.0 / frame_interval, 3)
            intervals = [t2 - t1 for t1,
                         t2 in zip(self.frame_times[:-1], self.frame_times[1:])]
            avg_interval = sum(intervals) / len(intervals)
            true_fps = 1.0 / avg_interval
            print(f"True screen FPS: {true_fps:.2f}")
            print("Actual FPS:",  fps, "  Time index: ", round(time_index, 3),
                  "  Frame number: ", self.frame_number, 'time:', round(elapsed-self.time_stamp, 3), 'dt:', round(elapsed-self.time_stamp-self.previous_time, 3))
        else:
            pass
        if frame_interval > 0:
            fps = round(1.0 / frame_interval, 3)
            # print("Actual FPS:",  fps, "  Time index: ", round(time_index,3),
            # "  Frame number: ", self.frame_number, 'time:', round(elapsed-self.time_stamp,3), 'dt:', round(elapsed-self.time_stamp-self.previous_time,3))
        else:
            time_index = 0.0
            fps = 60
            # print("Actual FPS: inf")
        self.last_time = now
        self.previous_time = elapsed-self.time_stamp
        p = self.params
        distanceToMonitor = self.dataParams[17]
        pixel_metre_ratio = self.dataParams[18]
        conditionVALUE = self.condition_dictionary[1]
        kwargs = {
            'frequency': conditionVALUE[0], 'position': conditionVALUE[1], 'general': conditionVALUE[2]}
        fs = float(kwargs['frequency'])
        phase_degree = float(kwargs['general'])
        admTEXT = self.dataParamsMain[0]
        # cL                  = funcs.adMethod_luminance_ID( admTEXT, self.fileParams, self.filesDataMain)
        # frame_number        = self.dataParams[len(self.dataParams)-1]
        stimulus_amplitude = p.diff_bkg
        bkg_contrast = self.dataParams[12]
        # Time (in seconds) for the current frame
        # print()
        # time_sec                = elapsed-self.time_stamp
        cL_flick = flicker_update_smooth(
            self, stimulus_amplitude, bkg_contrast, flicker_freq=fs, time_sec=time_index, phasedegree=phase_degree)
        self.frame_number += 1.0
        # self.dataParams[len(self.dataParams)-1] = frame_number
        # to_Text(self.fileParams,       self.dataParams)
        """
        Update the shader uniforms with the new values.
        This is where we pass the flicker contrast and time index to the shader.
        """
        x, y = self.pos
        w2 = self.w/2.0
        glUseProgram(self.program)
        glPushMatrix()
        glLoadIdentity()
        # <- added; updates argument in shader code.
        glUniform1f(self.uniforms['diff_bkg'], cL_flick)
        # glUniform1f(self.uniforms['probe_contrast'], cL) # <- added; updates argument in shader code.
        # glUniform1f(self.uniforms['time_index'], time_index) # <- added; updates argument in shader code.
        # glUniform1f(self.uniforms['frame_number'], self.frame_number) # <- added; updates argument in shader code.
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)


class two_lines_Apart(stim(th=0.0, R=50.0, d=3.0, alpha=1.0, a=10.0, b=10.0, width=0.5, bkg=0.0, diff_bkg=0.018, center_x=0.0, center_y=0.0, ppd_x=76.6, ppd_y=71.9,)):
    """Orientation circle stimulus
    
    :param th: size of stimulus
    :param R: radius
    :param d: width of orientation bar
    :param width: width of ellipse
    :param diff_bkg: difference added to background contrast
    """
    frag_source = """
    uniform float th, sigma, gap, alpha, a, b, width, bkg, diff_bkg, center_x, center_y, ppd_x, ppd_y;
    float edge = 40.0;

    float lined(float t, float x, float y) {
        return abs(-sin(t)*x+cos(t)*y);
    }

    float g(float x, float s2, float e2) {
        return exp(-0.5*pow(abs(x)/s2,e2));
    }
    
    void main( void ) {
        //float x = gl_TexCoord[0].x - 0.5;
        //float y = -(gl_TexCoord[0].y - 0.5);
        
        float x = gl_FragCoord.x; // — Screen Pixel Coordinates
        float y = gl_FragCoord.y; // — Screen Pixel Coordinates

        // Convert texture coordinates to screen pixel coordinates directly
        float x_px = x; // 0 to screen_width_pixels
        float y_px = y; // 0 to screen_height_pixels

        // Convert to degrees of visual angle
        float x_deg = (x_px - center_x) / ppd_x;
        float y_deg = (y_px - center_y) / ppd_y;
        
 
        // Compute the square equation
        // Parameters to position bars at ±offset
        float bar_offset = a;  // Distance from center to each bar
        float half_width = width / 2.0;
        
        bool in_right_bar = (x_deg >= bar_offset - half_width) && (x_deg <= bar_offset + half_width);
        bool in_left_bar  = (x_deg >= -bar_offset - half_width) && (x_deg <= -bar_offset + half_width);
        bool in_bar = (in_right_bar || in_left_bar);
        
        // Check vertical bounds
        bool in_height = (y_deg <= b) && (y_deg >= -b);
        
        float c = (in_bar && in_height) ? diff_bkg : bkg; 

        gl_FragColor = vec4( c,c,c,alpha );
    }
    """

    def __init__(self, pos, posCentre, fileParams, fileADM_cond, filePosition, params=Params()):
        import Functions.functionUSE as funcs
        import time
        self.start_specfic_t = time.perf_counter()
        self.time_stamp = 0.0
        self.frame_number = 0.0
        self.pos = pos
        self.posCentre = posCentre
        self.fileParams = fileParams
        self.filePosition = filePosition
        self.fileADM_cond = fileADM_cond
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms       = dict(map(self.shader.uniform, ['th', 'sigma', 'gap', 'alpha', 'a', 'b', 'width', 'bkg', 'diff_bkg','center_x', 'center_y',
                                                             'ppd_x', 'ppd_y']))
        self.dataParams = from_Text(self.fileParams)
        self.dataPosition = from_Text(self.filePosition)
        self.condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        glUseProgram(self.program)
        self.w = p.R*2.5
        glUniform1f(self.uniforms['th'], p.th)
        glUniform1f(self.uniforms['sigma'], 0.4)  # 0.4
        glUniform1f(self.uniforms['gap'], p.d/self.w)
        glUniform1f(self.uniforms['alpha'], p.alpha)
        glUniform1f(self.uniforms['a'], p.a)
        glUniform1f(self.uniforms['b'], p.b)
        glUniform1f(self.uniforms['center_x'], self.pos[0])
        glUniform1f(self.uniforms['center_y'], self.pos[1])
        glUniform1f(self.uniforms['ppd_x'], p.ppd_x)
        glUniform1f(self.uniforms['ppd_y'], p.ppd_y)
        glUniform1f(self.uniforms['width'], p.width)
        glUniform1f(self.uniforms['bkg'], p.bkg)
        glUniform1f(self.uniforms['diff_bkg'], p.diff_bkg)
        glUseProgram(0)

    def draw(self):
        import time
        import Functions.functionUSE as funcs
        self.dataParams = from_Text(self.fileParams)
        self.condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        p = self.params
        distanceToMonitor = self.dataParams[17]
        pixel_metre_ratio = self.dataParams[18]
        conditionVALUE = self.condition_dictionary[1]
        kwargs = {'frequency': conditionVALUE[0], 'position': conditionVALUE[1], 'general': conditionVALUE[2]}
        fs = float(kwargs['frequency'])
        phase_degree = float(kwargs['general'])
        end_time = time.perf_counter()
        # start_timer             = self.dataParams[33]
        self.frame_number = self.dataParams[len(self.dataParams)-1]
        elapsed = end_time - self.start_specfic_t
        time_index = float(self.frame_number / 60.0)
        stimulus_amplitude = p.diff_bkg
        bkg_contrast = self.dataParams[12]
        monitor_refresh_rate = self.dataParams[31]
        if self.frame_number <= 0:
            self.time_stamp = elapsed
        else:
            pass
        time_sec = elapsed-self.time_stamp
        cL_flick = flicker_update_smooth(
            self, stimulus_amplitude, bkg_contrast, flicker_freq=fs, time_sec=time_index, phasedegree=phase_degree)
        self.frame_number += 1
        self.dataParams[len(self.dataParams)-1] = self.frame_number
        to_Text(self.fileParams,       self.dataParams)

        x, y = self.pos
        w2 = self.w/2.0
        glUseProgram(self.program)
        glPushMatrix()
        glLoadIdentity()
        # <- added; updates argument in shader code.
        glUniform1f(self.uniforms['diff_bkg'], cL_flick)
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)


class two_lines_Apart_old(stim(th=0.0, R=50.0, d=3.0, alpha=1.0, a=10.0, b=10.0, width=0.5, bkg=0.0, diff_bkg=0.018)):
    """Orientation circle stimulus
    
    :param th: size of stimulus
    :param R: radius
    :param d: width of orientation bar
    :param width: width of ellipse
    :param diff_bkg: difference added to background contrast
    """
    frag_source = """
    uniform float th, sigma, gap, alpha, a, b, width, bkg, diff_bkg;
    float edge = 40.0;

    float lined(float t, float x, float y) {
        return abs(-sin(t)*x+cos(t)*y);
    }

    float g(float x, float s2, float e2) {
        return exp(-0.5*pow(abs(x)/s2,e2));
    }
    
    void main( void ) {
        float x = gl_TexCoord[0].x - 0.5;
        float y = -(gl_TexCoord[0].y - 0.5);
        
        
        // Compute the ellipse equation
        float ellipse = (x*x) / (a*a) + (y*y) / (b*b);
        
        // Compute the square equation
        float square_x  = abs(x);
        float square_y  = y;

        float outerBoundary_x = a;
        float innerBoundary_x = a - width; 

        float outerBoundary_y = b;
        float innerBoundary_y = -b; 

        //float c = ((square_x >= outerBoundary_x*(-1.0) && square_x <= innerBoundary_x*(-1.0) && square_y <= outerBoundary_y && square_y >= innerBoundary_y) || (square_x <= outerBoundary_x && square_x >= innerBoundary_x && square_y <= outerBoundary_y && square_y >= innerBoundary_y)) ? diff_bkg : bkg;
        // note ? means if statemnt before is true the continue with ? "" otherwise use : "".
        float c = ((square_x <= outerBoundary_x && square_x >= innerBoundary_x && square_y <= outerBoundary_y && square_y >= innerBoundary_y)) ? diff_bkg : bkg;

        //if ((square_x >= outerBoundary_x*(-1.0) && square_x <= innerBoundary_x*(-1.0) && square_y <= outerBoundary_y && square_y >= innerBoundary_y) || (square_x <= outerBoundary_x && square_x >= innerBoundary_x && square_y <= outerBoundary_y && square_y >= innerBoundary_y)) {
        //    float c =  diff_bkg; 
        //} else {
        //    float c = bkg;
        //}
        gl_FragColor = vec4( c,c,c,alpha );
    }
    """

    def __init__(self, pos, posCentre, fileParams, fileADM_cond, filePosition, params=Params()):
        self.pos = pos
        self.posCentre = posCentre
        self.fileParams = fileParams
        self.filePosition = filePosition
        self.fileADM_cond = fileADM_cond
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.shader = Shader(self.frag_source)
        self.program = self.shader.program
        self.uniforms       = dict(map(self.shader.uniform, ['th', 'sigma', 'gap', 'alpha', 'a', 'b', 'width', 'bkg', 'diff_bkg']))
        glUseProgram(self.program)
        self.w = p.R*2.5
        glUniform1f(self.uniforms['th'], p.th)
        glUniform1f(self.uniforms['sigma'], 0.4)  # 0.4
        glUniform1f(self.uniforms['gap'], p.d/self.w)
        glUniform1f(self.uniforms['alpha'], p.alpha)
        glUniform1f(self.uniforms['a'], p.a)
        glUniform1f(self.uniforms['b'], p.b)
        glUniform1f(self.uniforms['width'], p.width)
        glUniform1f(self.uniforms['bkg'], p.bkg)
        glUniform1f(self.uniforms['diff_bkg'], p.diff_bkg)
        glUseProgram(0)

    def draw(self):
        p = self.params
        import Functions.functionUSE as funcs
        dataParams = from_Text(self.fileParams)
        self.dataPosition = from_Text(self.filePosition)
        # posx                = (self.dataPosition[0])
        distanceToMonitor = dataParams[17]
        pixel_metre_ratio = dataParams[18]
        # pxDegree = (funcs.convertPixelToArcangle(
        #    posx, distanceToMonitor, pixel_metre_ratio))*0.16
        condition_dictionary = funcs.readText_toList_keyValue(
            self.fileADM_cond)
        conditionVALUE = condition_dictionary[1]
        kwargs = {
            'frequency': conditionVALUE[0], 'position': conditionVALUE[1]}
        fs = float(kwargs['frequency'])
        frame_number = dataParams[len(dataParams)-1]
        probe_contrast = p.diff_bkg
        bkg_contrast = dataParams[12]
        frame_number += 1
        cL_flick = flicker_update_smooth(
            self, frame_number, probe_contrast, bkg_contrast, flicker_freq=fs, monitor_refresh_rate=60)
        # params.color = (cL_flick, cL_flick, cL_flick, 1.0)
        dataParams[len(dataParams)-1] = frame_number
        to_Text(self.fileParams,       dataParams)

        x, y = self.pos
        w2 = self.w/2.0
        glUseProgram(self.program)
        glPushMatrix()
        glLoadIdentity()
        # <- added; updates argument in shader code.
        glUniform1f(self.uniforms['diff_bkg'], cL_flick)
        # glUniform1f(self.uniforms['a'], pxDegree)
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(-w2, -w2)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(w2, -w2)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(w2, w2)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(-w2, w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)


def flicker_update_smooth_bkgUP(self, probe_contrast, bkg_contrast, flicker_freq=10, time_sec=0, phasedegree=0):
    import numpy as np
    """
    Generate a sinusoidal flicker contrast signal instead of a square wave.
    - `probe_contrast` = peak amplitude of modulation, == 1.0 or 0.0
    - `bkg_contrast`   = baseline contrast offset
    - `flicker_freq`   = desired temporal frequency in Hz
    - `monitor_refresh_rate` = screen refresh rate (e.g., 60 Hz)
    - `phasedegree`    = phase offset in degrees (optional, default is 0)
    """

    # Convert phase from degrees to radians
    phaseradians = np.deg2rad(phasedegree)

    # Time (in seconds) for the current frame
    t = time_sec  # frame_number / monitor_refresh_rate

    # Sinusoidal contrast value oscillating between -1 and +1
    oscillation = abs(np.sin((2 * np.pi * flicker_freq * t)-phaseradians))

    # Scale and shift to desired amplitude and baseline
    contrast_c = bkg_contrast + (1.0-bkg_contrast)*oscillation*probe_contrast

    return contrast_c


def flicker_update_smooth(self, probe_contrast, bkg_contrast, flicker_freq=10, time_sec=0, phasedegree=0):
    import numpy as np
    """
    Generate a sinusoidal flicker contrast signal instead of a square wave.
    - `probe_contrast` = peak amplitude of modulation
    - `bkg_contrast`   = baseline contrast offset
    - `flicker_freq`   = desired temporal frequency in Hz
    - `monitor_refresh_rate` = screen refresh rate (e.g., 60 Hz)
    - `phasedegree`    = phase offset in degrees (optional, default is 0)
    """

    # Convert phase from degrees to radians
    phaseradians = np.deg2rad(phasedegree)

    # Time (in seconds) for the current frame
    t = time_sec  # frame_number / monitor_refresh_rate

    # Sinusoidal contrast value oscillating between -1 and +1
    oscillation = np.sin((2 * np.pi * flicker_freq * t)-phaseradians)

    # Scale and shift to desired amplitude and baseline
    contrast_c = bkg_contrast + (bkg_contrast)*oscillation

    return contrast_c


def flicker_update(self, frame_number, probe_contrast, bkg_contrast, flicker_freq=10, monitor_refresh_rate=60):
    """
        @ ChatGpt ish: 
    """
    frames_per_cycle = int(monitor_refresh_rate / flicker_freq)
    # Simple square wave flicker
    if (frame_number % frames_per_cycle) < (frames_per_cycle // 2):
        # <- i.e to make sure amplitude peak and trough are the same  probe_contrast  # Visible
        contrast_c = bkg_contrast*2
    else:
        contrast_c = 0.0  # bkg_contrast  # black
    return contrast_c


class Line_ADM_Time(stim(length=100.0, width=10.0, angle=0.0, color=(1.0, 1.0, 1.0, 1.0))):
    def __init__(self, posCentre, pos, admTEXT, fileParamsMain, fileParams, fileParamsPosition, filesDataMain, params=Params()):
        self.pos = pos
        self.posCentre = posCentre
        self.NAN = admTEXT
        self.fileParams = fileParams
        self.filesDataMain = filesDataMain
        self.params = copy_params(self._defaults, params)
        self.filePosition = fileParamsPosition
        self.fileParamsMain = fileParamsMain

    def draw(self):
        import Functions.functionUSE as funcs
        self.dataPosition = from_Text(self.filePosition)
        self.px = self.pos[0]
        self.py = self.pos[1]
        dataParamsMain = from_Text(self.fileParamsMain)
        dataParams = from_Text(self.fileParams)
        frame_number = dataParams[len(dataParams)-1]
        params = self.params
        # funcs.adMethod_luminance_ID( admTEXT, self.fileParams, self.filesDataMain)
        probe_contrast = 1
        bkg_contrast = dataParams[12]
        frame_number += 1
        cL_flick = flicker_update(self, frame_number, probe_contrast,
                                  bkg_contrast, flicker_freq=5, monitor_refresh_rate=60)

        params.color = (cL_flick, cL_flick, cL_flick, 1.0)
        self.pos = [self.px, self.py]

        dataParams[len(dataParams)-1] = frame_number
        to_Text(self.fileParams,       dataParams)
        """
        Then save to a file for posX and posY only, which can be accesed by "ADM trial".
        """
        if hasattr(params, 'color') and not iterable(params.color):
            params.color = [params.color]*3
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1, 2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.length, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.params.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()


class Line_ADM_Time_main(stim(length=100.0, width=10.0, angle=0.0, color=(1.0, 1.0, 1.0, 1.0))):
    def __init__(self, posCentre, pos, admTEXT, fileParamsMain, fileParams, fileParamsPosition, filesDataMain, params=Params()):
        self.pos = pos
        self.posCentre = posCentre
        self.NAN = admTEXT
        self.fileParams = fileParams
        self.filesDataMain = filesDataMain
        self.params = copy_params(self._defaults, params)
        self.filePosition = fileParamsPosition
        self.fileParamsMain = fileParamsMain

    def draw(self):
        import Functions.functionUSE as funcs
        self.dataPosition = from_Text(self.filePosition)
        self.px = self.pos[0]
        self.py = self.pos[1]
        dataParamsMain = from_Text(self.fileParamsMain)
        dataParams = from_Text(self.fileParams)
        # admTEXT # <- needs to be accesed just like position.
        admTEXT = dataParamsMain[0]

        frame_number = dataParams[len(dataParams)-1]
        params = self.params
        # funcs.adMethod_luminance_ID( admTEXT, self.fileParams, self.filesDataMain)
        probe_contrast = 1

        bkg_contrast = dataParams[12]
        frame_number += 1
        cL_flick = flicker_update(self, frame_number, probe_contrast,
                                  bkg_contrast, flicker_freq=5, monitor_refresh_rate=60)

        params.color = (cL_flick, cL_flick, cL_flick, 1.0)
        self.pos = [self.px, self.py]

        dataParams[len(dataParams)-1] = frame_number
        to_Text(self.fileParams,       dataParams)
        """
        Then save to a file for posX and posY only, which can be accesed by "ADM trial".
        """
        if hasattr(params, 'color') and not iterable(params.color):
            params.color = [params.color]*3
        self.params = copy_params(self._defaults, params)
        p = self.params
        self.clock = pyglet.clock.Clock()
        self.t0 = self.clock.time()
        # make indexed vertex_list
        ind = array([0, 1, 2, 0, 2, 3])
        xy = r_[0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0].reshape(-1,2) - 0.5
        self.vlist = pyglet.graphics.vertex_list_indexed(
            4, ind, 'v2d/stream', 'c4f')
        N = 4
        self.xy = from_ctypes(self.vlist.vertices, 'f8', (N, 2))
        self.xy[...] = xy * r_[p.length, p.width]
        self.colors = from_ctypes(self.vlist.colors, 'f4', (N, 4))
        self.colors[:, 3] = 1.0
        self.colors[:, :len(p.color)] = p.color
        self.vlist._vertices_cache.invalidate()
        self.vlist._colors_cache.invalidate()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0], self.pos[1], 0.0)
        glRotatef(self.params.angle, 0.0, 0.0, 1.0)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_MULTISAMPLE_ARB)
        # glEnable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        self.vlist.draw(GL_TRIANGLES)
        glEnable(GL_TEXTURE_2D)
        # glDisable(GL_POLYGON_SMOOTH);
        # glHint(GL_POLYGON_SMOOTH_HINT, GL_DONT_CARE)
        glDisable(GL_MULTISAMPLE_ARB)
        glPopMatrix()

# =============================================================================
#
# =============================================================================
