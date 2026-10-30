#include <jni.h>
#include <GLES3/gl3.h>
#include <android/log.h>
#include <vector>
#include <cmath>
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR,"RealmForge",__VA_ARGS__)
static GLuint program=0, vao=0;
static int width=0,height=0;
static GLuint compile(GLenum kind,const char* source) {
 GLuint s=glCreateShader(kind); glShaderSource(s,1,&source,nullptr); glCompileShader(s);
 GLint ok=0; glGetShaderiv(s,GL_COMPILE_STATUS,&ok);
 if(!ok){char log[1024]={};glGetShaderInfoLog(s,sizeof(log),nullptr,log);LOGE("%s",log);glDeleteShader(s);return 0;}
 return s;
}
extern "C" JNIEXPORT jboolean JNICALL Java_com_realmforge_engine_NativeRenderer_initRenderer(JNIEnv*,jobject,jint w,jint h) {
 if(w<=0||h<=0||w>4096||h>4096||!glGetString(GL_RENDERER))return JNI_FALSE;
 width=w;height=h;
 const char* vs="#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID==2)?3.0:-1.0,(gl_VertexID==1)?3.0:-1.0);gl_Position=vec4(p,0.0,1.0);}";
 const char* fs="#version 300 es\nprecision highp float;uniform float uTime;uniform vec2 uResolution;out vec4 color;void main(){vec2 uv=(gl_FragCoord.xy/uResolution)*2.0-1.0;uv.x*=uResolution.x/uResolution.y;float r=length(uv);float glow=0.025/max(0.015,abs(r-0.4-0.1*sin(uTime*2.0)));color=vec4(vec3(glow*0.2,glow*0.45,glow),1.0);}";
 GLuint v=compile(GL_VERTEX_SHADER,vs),f=compile(GL_FRAGMENT_SHADER,fs);
 if(!v||!f){if(v)glDeleteShader(v);if(f)glDeleteShader(f);return JNI_FALSE;}
 GLuint p=glCreateProgram();glAttachShader(p,v);glAttachShader(p,f);glLinkProgram(p);
 glDeleteShader(v);glDeleteShader(f);
 GLint ok=0;glGetProgramiv(p,GL_LINK_STATUS,&ok);
 if(!ok){glDeleteProgram(p);return JNI_FALSE;}
 if(program)glDeleteProgram(program);program=p;
 if(!vao)glGenVertexArrays(1,&vao);
 return JNI_TRUE;
}
extern "C" JNIEXPORT jboolean JNICALL Java_com_realmforge_engine_NativeRenderer_drawFrame(JNIEnv*,jobject,jfloat seconds){
 if(!program||!vao)return JNI_FALSE;
 glViewport(0,0,width,height);glUseProgram(program);glBindVertexArray(vao);
 glUniform1f(glGetUniformLocation(program,"uTime"),seconds);
 glUniform2f(glGetUniformLocation(program,"uResolution"),(float)width,(float)height);
 glDrawArrays(GL_TRIANGLES,0,3);return glGetError()==GL_NO_ERROR?JNI_TRUE:JNI_FALSE;
}
extern "C" JNIEXPORT void JNICALL Java_com_realmforge_engine_NativeRenderer_release(JNIEnv*,jobject){
 if(program){glDeleteProgram(program);program=0;}
 if(vao){glDeleteVertexArrays(1,&vao);vao=0;}
}
