import { useEffect, useRef, useState } from 'react';

interface Props { engineId: string; rotate: boolean; reset: number; poster: string; onStatus: (text: string) => void }
export default function EngineStage({ engineId, rotate, reset, poster, onStatus }: Props) {
  const mount = useRef<HTMLDivElement>(null);
  const rotation = useRef(rotate);
  const resetCamera = useRef<(() => void) | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  rotation.current = rotate;
  useEffect(() => { resetCamera.current?.(); }, [reset]);
  useEffect(() => {
    const element = mount.current;
    if (!element) return;
    let cancelled = false;
    let clean = () => {};
    const controller = new AbortController();
    setReady(false);setFailed(false);onStatus('Preparing interactive engine…');
    const start = performance.now();
    async function load() {
      const [THREE, {GLTFLoader}, {DRACOLoader}, {OrbitControls}, {RoomEnvironment}] = await Promise.all([
        import('three'), import('three/examples/jsm/loaders/GLTFLoader.js'), import('three/examples/jsm/loaders/DRACOLoader.js'),
        import('three/examples/jsm/controls/OrbitControls.js'), import('three/examples/jsm/environments/RoomEnvironment.js'),
      ]);
      if (cancelled || !element) return;
      const renderer = new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'high-performance'});
      renderer.setPixelRatio(Math.min(devicePixelRatio,1.75));
      renderer.setClearColor(0,0);
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = .85;
      element.appendChild(renderer.domElement);
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(32,1,0.01,100);
      const controls = new OrbitControls(camera,renderer.domElement);
      controls.enableDamping=true;controls.enablePan=false;controls.autoRotateSpeed=.55;
      controls.minDistance=2.5;controls.maxDistance=8;
      const pmrem = new THREE.PMREMGenerator(renderer);
      const environment = new RoomEnvironment();
      const envTarget=pmrem.fromScene(environment,.04);
      scene.environment=envTarget.texture;
      scene.environmentIntensity=.7;
      environment.dispose();pmrem.dispose();
      const key = new THREE.DirectionalLight(0xdce9ff,1.5);key.position.set(3,4,5);scene.add(key);
      const blue = new THREE.DirectionalLight(0x1558ff,2);blue.position.set(-3,1,-2);scene.add(blue);
      const rim = new THREE.DirectionalLight(0xd4ff24,1);rim.position.set(2,2,-4);scene.add(rim);
      let frame=0;let visible=true;let model: import('three').Group | null=null;
      const resize = () => {const w=element.clientWidth,h=element.clientHeight;if(!w||!h)return;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();resetCamera.current?.();};
      const observer=new ResizeObserver(resize);observer.observe(element);
      const visibility=new IntersectionObserver(([entry])=>{visible=entry.isIntersecting;});visibility.observe(element);
      const disposeModel=(root: import('three').Object3D)=>{root.traverse(object=>{const mesh=object as import('three').Mesh;if(!mesh.isMesh)return;mesh.geometry.dispose();const mats=Array.isArray(mesh.material)?mesh.material:[mesh.material];for(const material of mats){for(const value of Object.values(material))if(value && typeof value==='object' && 'isTexture' in value)(value as import('three').Texture).dispose();material.dispose();}});};
      const draco = new DRACOLoader();draco.setDecoderPath('/draco/');draco.setWorkerLimit(2);
      clean=()=>{cancelAnimationFrame(frame);observer.disconnect();visibility.disconnect();controls.dispose();draco.dispose();envTarget.dispose();if(model)disposeModel(model);renderer.dispose();renderer.domElement.remove();resetCamera.current=null;};
      const loader=new GLTFLoader();loader.setDRACOLoader(draco);
      resize();
      const response=await fetch(`/studio/models/${engineId}.glb`,{signal:controller.signal});
      if(!response.ok)throw Error(`Model request returned ${response.status}`);
      const bytes=await response.arrayBuffer();
      if(cancelled)return;
      onStatus('Unpacking the engine…');
      const gltf=await loader.parseAsync(bytes,'/studio/models/');
      if(cancelled){disposeModel(gltf.scene);return;}
      model=gltf.scene;
      const bounds=new THREE.Box3().setFromObject(model);
      const center=bounds.getCenter(new THREE.Vector3());
      const size=bounds.getSize(new THREE.Vector3());
      const scale=2.35/Math.max(size.x,size.y,size.z);
      model.position.sub(center);const group=new THREE.Group();group.add(model);group.scale.setScalar(scale);scene.add(group);
      const home=()=>{const aspect=element.clientWidth/element.clientHeight;const distance=aspect<.9?6.8:5.1;camera.position.set(distance*.65,distance*.32,distance*.68);controls.target.set(0,0,0);controls.update();};
      resetCamera.current=home;home();
      await renderer.compileAsync(scene,camera);
      if(cancelled)return;
      renderer.render(scene,camera);
      setReady(true);
      const elapsed=(performance.now()-start)/1000;
      onStatus(`Drag to orbit · scroll to zoom · ready in ${elapsed.toFixed(1)}s`);
      element.dataset.readySeconds=elapsed.toFixed(3);
      const animate=()=>{frame=requestAnimationFrame(animate);if(!visible||document.hidden)return;controls.autoRotate=rotation.current && !matchMedia('(prefers-reduced-motion: reduce)').matches;controls.update();renderer.render(scene,camera);};animate();
    }
    load().catch(error=>{if(cancelled)return;console.error('Engine stage:',error);clean();setFailed(true);onStatus('Interactive view unavailable. Studio image is still available.');});
    return ()=>{cancelled=true;controller.abort();clean();};
  },[engineId,retry,onStatus]);
  return <><img className={`studio-engine-poster studio-stage-fallback ${ready ? 'is-hidden' : ''}`} src={poster} alt="Engine studio preview"/><div className={`studio-webgl ${ready ? 'is-ready' : ''}`} ref={mount} role="img" aria-label="Interactive engine model. Drag to orbit and use the scroll wheel to zoom."/>{failed&&<button className="studio-retry" onClick={()=>setRetry(v=>v+1)}>Retry 3D</button>}</>;
}
