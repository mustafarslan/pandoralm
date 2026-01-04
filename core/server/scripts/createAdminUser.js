// Script to create admin user
// Run from within the core server context

const bcrypt = require('bcryptjs');
const prisma = require('./utils/prisma');

async function createAdminUser() {
    try {
        // Check if user exists
        const existing = await prisma.users.findFirst({ where: { username: 'admin@example.com' } });
        if (existing) {
            console.log('User already exists, updating role to admin...');
            await prisma.users.update({
                where: { id: existing.id },
                data: { role: 'admin', password: bcrypt.hashSync('password123', 10) }
            });
            console.log('User updated successfully');
        } else {
            console.log('Creating new admin user...');
            await prisma.users.create({
                data: {
                    username: 'admin@example.com',
                    password: bcrypt.hashSync('password123', 10),
                    role: 'admin'
                }
            });
            console.log('Admin user created successfully');
        }
        await prisma.$disconnect();
    } catch (e) {
        console.error('Error:', e.message);
        await prisma.$disconnect();
        process.exit(1);
    }
}

createAdminUser();
