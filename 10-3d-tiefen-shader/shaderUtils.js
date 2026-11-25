export function createDepthShader() {
    return `
        precision highp float;
        uniform vec3 u_camPos;
        uniform vec3 u_camTarget;
        uniform float u_fov;
        uniform float u_time;
        uniform vec2 u_resolution;
        varying vec2 vUv;
        float sdSphere(vec3 p, float r) { return length(p) - r; }
        float sdBox(vec3 p, vec3 b) { vec3 q = abs(p) - b; return length(max(q,0.0)) + min(max(q.x,max(q.y,q.z)),0.0); }
        float mapDepth(vec3 p) {
            float d = sdSphere(p, 2.0);
            d = min(d, sdBox(p - vec3(3.0, 0.0, 0.0), vec3(1.5)));
            d = min(d, sdBox(p - vec3(-3.0, 0.0, 0.0), vec3(1.5)));
            return d;
        }
        void main() {
            vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution) / u_resolution.y;
            vec3 ro = u_camPos;
            vec3 ta = u_camTarget;
            vec3 f = normalize(ta - ro);
            vec3 r = normalize(cross(vec3(0.0,1.0,0.0), f));
            vec3 u = cross(f, r);
            float fov = radians(u_fov);
            vec3 rd = normalize((r * uv.x + u * uv.y) * tan(fov * 0.5) + f);
            float t = 0.0;
            for(int i=0;i<64;i++){
                vec3 p = ro + rd * t;
                float h = mapDepth(p);
                if(h < 0.0005) break;
                t += h;
                if(t>120.0) break;
            }
            float depth = t / 120.0;
            gl_FragColor = vec4(depth,0.0,0.0,1.0);
        }
    `;
}