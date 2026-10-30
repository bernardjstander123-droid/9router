#include <jni.h>
#include <GLES3/gl3.h>
#include <android/log.h>
#include <vector>
#include <cmath>
static GLuint prog=0,vao=0;
static int W=0,H=0;
static GLuint shader(GLenum type,const char* src){GLuint s=glCreateShader(type);glShaderSource(s,1,&src,nullptr);glCompileShader(s);GLint ok=0;glGetShaderiv(s,GL_COMPILE_STATUS,&ok);if(!ok){glDeleteShader(s);return 0;}return s;}
extern "C" JNIEXPORT jboolean JNICALL Java_com_realmforge_engine_NativeRenderer_initRenderer(JNIEnv*,jobject,jint w,jint h,jint fps,jfloat duration){
 if(w<1||h<1||w>4096||h>4096||fps<1||duration<=0||!glGetString(GL_RENDERER))return JNI_FALSE;
 W=w;H=h;
 const char* vs="#version 300 es\nvoid main(){vec2 p=vec2(gl_VertexID==2?3.0:-1.0,gl_VertexID==1?3.0:-1.0);gl_Position=vec4(p,0.,1.);}";
 const char* fs="#version 300 es\nprecision highp float;uniform float t;uniform vec2 size;out vec4 c;void main(){vec2 uv=2.*gl_FragCoord.xy/size-1.;uv.x*=size.x/size.y;float r=length(uv);float g=0.025/max(.01,abs(r-.4-.1*sin(t*2.)));c=vec4(min(vec3(.1,.3,.7)*g,1.),1.);}";
 GLuint v=shader(GL_VERTEX_SHADER,vs),f=shader(GL_FRAGMENT_SHADER,fs);if(!v||!f)return JNI_FALSE;
 GLuint p=glCreateProgram();glAttachShader(p,v);glAttachShader(p,f);glLinkProgram(p);glDeleteShader(v);glDeleteShader(f);GLint ok=0;glGetProgramiv(p,GL_LINK_STATUS,&ok);if(!ok){glDeleteProgram(p);return JNI_FALSE;}if(prog)glDeleteProgram(prog);prog=p;if(!vao)glGenVertexArrays(1,&vao);return JNI_TRUE;
}
extern "C" JNIEXPORT jbyteArray JNICALL Java_com_realmforge_engine_NativeRenderer_renderFrame(JNIEnv* env,jobject,jint index,jfloat seconds){
 if(!prog||!vao)return nullptr;glViewport(0,0,W,H);glUseProgram(prog);glBindVertexArray(vao);glUniform1f(glGetUniformLocation(prog,"t"),seconds);glUniform2f(glGetUniformLocation(prog,"size"),W,H);glDrawArrays(GL_TRIANGLES,0,3);
 std::vector<unsigned char> rgba((size_t)W*H*4);glReadPixels(0,0,W,H,GL_RGBA,GL_UNSIGNED_BYTE,rgba.data());if(glGetError()!=GL_NO_ERROR)return nullptr;
 // OpenGL origin bottom-left; reverse rows for Android top-left byte consumers.
 size_t stride=(size_t)W*4;for(int y=0;y<H/2;y++)for(size_t x=0;x<stride;x++)std::swap(rgba[(size_t)y*stride+x],rgba[(size_t)(H-1-y)*stride+x]);
 jbyteArray out=env->NewByteArray((jsize)rgba.size());if(out)env->SetByteArrayRegion(out,0,(jsize)rgba.size(),(jbyte*)rgba.data());return out;
}
extern "C" JNIEXPORT void JNICALL Java_com_realmforge_engine_NativeRenderer_releaseRenderer(JNIEnv*,jobject){if(prog){glDeleteProgram(prog);prog=0;}if(vao){glDeleteVertexArrays(1,&vao);vao=0;}}
