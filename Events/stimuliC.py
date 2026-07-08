
from __future__ import division

from libC import *

from  Functions.functionsForUse import (
    read_JSON,
)
import numpy as np
from pyglet import text
import pyglet

### =========
class Grating_ADM(stim(width=200.0,fs=10.0,ph=0.0,speed=0.0,contr=1.0,theta=0.0,bg=0.5,
                   box=False,Lbg=24.65,Lmin=0.0,Lmax=49.3,gamma=2.5,BTRR=63.2, SdeX=0.05, SdeY=0.05)):
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
    ### m = exp(-0.5*(x*x + y*y)/pow(0.17,2.0));
    ### abs(sin(fs*x)+phase)
    ##  float Sde = 0.1;
    ##  double pi = 2 * acos(0.0);
    ### m = (1/(2*pi*pow(Sde,2)))*exp(-(pow(x,2)+pow(y,2))/(2*pow(Sde,2)))
    def __init__(self,pos, filename_Conditions,params=Params()):
        self.pos        = pos
        self.params     = copy_params(self._defaults,params)
        self.clock      = pyglet.clock.Clock()
        self.t0         = self.clock.time()
        self.shader     = Shader(self.frag_source)
        self.program    = self.shader.program
        self.uniforms   = dict(map(self.shader.uniform,
                                 ['fs','phase','contr','theta','bg','box','Lbg',
                                  'Lmin','Lmax','gamma','BTRR'
                                  ,'SdeX', 'SdeY'])) # <- added
        
        
        self.filename_Conditions = filename_Conditions

        glUseProgram(self.program)
        glUniform1f(self.uniforms['phase'],0.0)
        glUniform1f(self.uniforms['fs'],self.params.fs)
        glUniform1f(self.uniforms['contr'],self.params.contr)
        glUniform1f(self.uniforms['theta'],self.params.theta)
        glUniform1f(self.uniforms['bg'],self.params.bg)
        glUniform1f(self.uniforms['box'],self.params.box)
        glUniform1f(self.uniforms['Lbg'],self.params.Lbg)
        glUniform1f(self.uniforms['Lmin'],self.params.Lmin)
        glUniform1f(self.uniforms['Lmax'],self.params.Lmax)
        glUniform1f(self.uniforms['gamma'],self.params.gamma)
        glUniform1f(self.uniforms['BTRR'],self.params.BTRR)
        glUniform1f(self.uniforms['SdeX'],self.params.SdeX) # <- added
        glUniform1f(self.uniforms['SdeY'],self.params.SdeY) # <- added
        glUseProgram(0)
        
    def draw(self):
        
        self.px             = self.pos[0]
        self.py             = self.pos[1]

        data_conditions         = read_JSON(self.filename_Conditions)

        new_id               = data_conditions['staircase_Identity_now'][0]  
        stimulus_condition   = data_conditions['stimulus_condition'][new_id]
        probe_weber_contrast = data_conditions['now_weber_contrast'][new_id]       
        #probe_screen_intensity = data_conditions['now_screen_intensity'][new_id]     


        self.params.fs      = stimulus_condition
        cL                  = probe_weber_contrast
        self.params.contr   = cL # <-- actually give contrast value
        
        glUseProgram(self.program)
        glUniform1f(self.uniforms['fs'],   self.params.fs)
        glUniform1f(self.uniforms['contr'],self.params.contr)
        glUseProgram(0)
        
        p = self.params
        x, y = self.pos
        w2 = p.width/2.0
        glUseProgram(self.program)
        ph = p.speed*(self.clock.time()-self.t0)
        glUniform1f(self.uniforms['phase'],ph)
        #glUniform1f(self.uniforms['width'], p.width)  # Update width uniform  # <- added
        
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(self.pos[0],self.pos[1],0.0)
        glBegin(GL_QUADS)
        glTexCoord2f(0.0,1.0)
        glVertex2f(-w2,-w2)
        glTexCoord2f(1.0,1.0)
        glVertex2f(w2,-w2)
        glTexCoord2f(1.0,0.0)
        glVertex2f(w2,w2)
        glTexCoord2f(0.0,0.0)
        glVertex2f(-w2,w2)
        glEnd()
        glPopMatrix()
        glUseProgram(0)


### =========

class Dot_stairCase_centre(stim(c=1.0,sigma=0.17,fs=0.0,phi=0.0,edge=2.0,res=64, msg='Text',size=24)):
    """Gaussian dot stimulus with size control
    
    :param c: contrast [0.0,1.0]
    """
    def __init__(self, pos, bkg,fileCondition,params=Params()):
        self.params     = copy_params(self._defaults,params)
        self.fileCondition = fileCondition
        self.params.bkg = bkg
        
        self.params = copy_params(self._defaults,params)
        self.pos    = pos
        p           = self.params
        self.label  = text.Label(p.msg,
                          font_name='Times New Roman',
                          font_size=p.size,
                          anchor_x='center',
                          anchor_y='center',
                          x=self.pos[0], y=self.pos[1])
                          
        sigma   = self.params.sigma
        fs      = self.params.fs
        phi     = self.params.phi
        edge    = self.params.edge
        res     = self.params.res
        im      = make_dot(sigma,fs,phi,edge,res) # <-type of stimulus

        w = im.width
        h = im.height
        im.anchor_x     = w//2
        im.anchor_y     = h//2

        self.image0     = im
        self.posCentre  = pos
        
    def draw(self):
        data_conditions = read_JSON(self.fileCondition)
        terminateBOOL   = data_conditions['terminate_bool']
        if terminateBOOL == 0:
            c2 = self.params.c
            glColor4f(c2,c2,c2,1.0)
            self.image0.blit(self.posCentre[0], self.posCentre[1]) # <- add second stimulus
        elif terminateBOOL == 1:
            glEnable(GL_BLEND)
            glEnable(GL_TEXTURE_2D)
            self.label.draw()
        else:
            c2 = self.params.c
            glColor4f(c2,c2,c2,1.0)
            self.image0.blit(self.posCentre[0], self.posCentre[1]) # <- add second stimulus
        
### ========

class Text(stim(msg='Text',size=24)):
    """Text stimulus
    
    :param msg: string to display
    :params size: font size (default 24)
    """
    def __init__(self,pos,params=Params()):
        self.params = copy_params(self._defaults,params)
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

### ========

