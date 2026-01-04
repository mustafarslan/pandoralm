import React, { useEffect, useRef } from 'react';

const NeuralGraph = ({ position = 'bottom-left' }) => {
    const canvasRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let animationFrameId;

        // Set canvas size
        const resizeCanvas = () => {
            canvas.width = 500;
            canvas.height = 500;
        };
        resizeCanvas();

        // Node configuration
        const NODE_COUNT = 25;
        const CONNECTION_DISTANCE = 120;
        // const MOUSE_REPEL_RADIUS = 150; // Not implementing interaction for now to keep it ambient

        // Initialize nodes
        const nodes = Array.from({ length: NODE_COUNT }).map(() => ({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 0.8, // Velocity X
            vy: (Math.random() - 0.5) * 0.8, // Velocity Y
            radius: Math.random() * 2 + 2,
        }));

        const draw = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Update positions
            nodes.forEach(node => {
                node.x += node.vx;
                node.y += node.vy;

                // Wall bounce
                if (node.x < 0 || node.x > canvas.width) node.vx *= -1;
                if (node.y < 0 || node.y > canvas.height) node.vy *= -1;
            });

            // Draw connections
            ctx.lineWidth = 1;
            for (let i = 0; i < nodes.length; i++) {
                const nodeA = nodes[i];
                for (let j = i + 1; j < nodes.length; j++) {
                    const nodeB = nodes[j];
                    const dx = nodeA.x - nodeB.x;
                    const dy = nodeA.y - nodeB.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);

                    if (distance < CONNECTION_DISTANCE) {
                        const opacity = 1 - (distance / CONNECTION_DISTANCE);
                        ctx.beginPath();
                        ctx.strokeStyle = `rgba(125, 125, 125, ${opacity * 0.3})`; // #7D7D7D with opacity
                        ctx.moveTo(nodeA.x, nodeA.y);
                        ctx.lineTo(nodeB.x, nodeB.y);
                        ctx.stroke();
                    }
                }
            }

            // Draw nodes
            nodes.forEach(node => {
                ctx.beginPath();
                ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(37, 37, 37, 0.8)'; // #252525
                ctx.fill();
            });

            animationFrameId = requestAnimationFrame(draw);
        };

        draw();

        return () => {
            cancelAnimationFrame(animationFrameId);
        };
    }, []);

    // Dynamic styles based on position
    let positionClasses = '';
    let maskPosition = '';

    switch (position) {
        case 'top-left':
            positionClasses = 'top-0 left-0';
            maskPosition = 'top left';
            break;
        case 'top-right':
            positionClasses = 'top-0 right-0';
            maskPosition = 'top right';
            break;
        case 'bottom-right':
            positionClasses = 'bottom-0 right-0';
            maskPosition = 'bottom right';
            break;
        case 'bottom-left':
        default:
            positionClasses = 'bottom-0 left-0';
            maskPosition = 'bottom left';
            break;
    }

    const maskStyle = `radial-gradient(circle at ${maskPosition}, black 40%, transparent 80%)`;

    return (
        <div className={`absolute ${positionClasses} w-[500px] h-[500px] pointer-events-none opacity-60`}>
            <canvas
                ref={canvasRef}
                className="w-full h-full"
                style={{
                    maskImage: maskStyle,
                    WebkitMaskImage: maskStyle
                }}
            />
        </div>
    );
};

export default NeuralGraph;
