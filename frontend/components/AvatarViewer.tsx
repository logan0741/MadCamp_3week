'use client';

import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, ContactShadows } from '@react-three/drei';
import styles from '../app/mypage/mypage.module.css';

// Simple Avatar Component
function AvatarPlaceholder() {
    const group = useRef<any>();

    useFrame((state) => {
        if (group.current) {
            group.current.position.y = Math.sin(state.clock.elapsedTime) * 0.1;
        }
    });

    return (
        <group ref={group} position={[0, -1, 0]}>
            <mesh position={[0, 1.6, 0]}>
                <sphereGeometry args={[0.25, 32, 32]} />
                <meshStandardMaterial color="#FFD1DC" roughness={0.5} />
            </mesh>
            <mesh position={[0, 0.9, 0]}>
                <cylinderGeometry args={[0.25, 0.15, 1.4, 32]} />
                <meshStandardMaterial color="#333333" roughness={0.8} />
            </mesh>
            <mesh position={[-0.4, 1.1, 0]} rotation={[0, 0, -0.2]}>
                <cylinderGeometry args={[0.08, 0.06, 1, 16]} />
                <meshStandardMaterial color="#333333" />
            </mesh>
            <mesh position={[0.4, 1.1, 0]} rotation={[0, 0, 0.2]}>
                <cylinderGeometry args={[0.08, 0.06, 1, 16]} />
                <meshStandardMaterial color="#333333" />
            </mesh>
            <mesh position={[-0.15, -0.3, 0]}>
                <cylinderGeometry args={[0.08, 0.06, 1.2, 16]} />
                <meshStandardMaterial color="#1a1a1a" />
            </mesh>
            <mesh position={[0.15, -0.3, 0]}>
                <cylinderGeometry args={[0.08, 0.06, 1.2, 16]} />
                <meshStandardMaterial color="#1a1a1a" />
            </mesh>
        </group>
    );
}

export default function AvatarViewer() {
    return (
        <div className={styles.canvasWrapper}>
            <Canvas shadows dpr={[1, 2]}>
                <PerspectiveCamera makeDefault position={[0, 0, 4]} fov={50} />
                <ambientLight intensity={0.5} />
                <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={1} castShadow />
                <pointLight position={[-10, -10, -10]} intensity={0.5} />

                <AvatarPlaceholder />

                <ContactShadows resolution={1024} scale={10} blur={2} opacity={0.5} far={10} color="#000000" />
                <OrbitControls minPolarAngle={Math.PI / 4} maxPolarAngle={Math.PI / 2} enableZoom={true} enablePan={false} />
            </Canvas>
        </div>
    );
}
