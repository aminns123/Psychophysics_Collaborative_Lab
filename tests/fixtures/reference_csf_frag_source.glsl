
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
        uniform float physicalFrequency;
        uniform float pitchX, pitchY, eyeDistance;
        uniform float screenCx, screenCy, stimCx, stimCy;
        
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
            // In cpd mode the phase is computed from the physical angular
            // coordinate of every fragment, not an uncalibrated legacy scalar.
            // This also avoids a screen-wide-FOV approximation near eccentricity.
            vec2 phase_coords = vec2(x, y);
            float frequency_phase = fs * (x*cos(theta)+y*sin(theta));
            if (physicalFrequency > 0.5) {
                vec2 pitch = vec2(pitchX, pitchY);
                vec2 screen_centre = vec2(screenCx, screenCy);
                vec2 monitor_px = vec2(stimCx,stimCy) + phase_coords * width;
                vec2 screen_m = (monitor_px - screen_centre) * pitch;
                vec2 centre_m = (vec2(stimCx,stimCy)-screen_centre)*pitch;
                vec2 degrees_relative = degrees(atan(screen_m / eyeDistance))
                                       - degrees(atan(centre_m / eyeDistance));
                float pi = 2.0 * acos(0.0);
                frequency_phase = 2.0 * pi * fs
                    * (degrees_relative.x * cos(theta)
                       + degrees_relative.y * sin(theta));
            }
            float c = m*contr*sin(frequency_phase + phase);
            if (box == 1.0) {
                gl_FragColor.rgba = vec4(lum2image(c),1.0);
            } else {
                c = bg + c/2.0;
                gl_FragColor.rgba = vec4(c,c,c,1.0);
            }
        }
        