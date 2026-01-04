
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
    const workspaces = await prisma.workspaces.findMany();
    console.log("All Workspaces:");
    workspaces.forEach(w => {
        console.log(`- Name: ${w.name}, Slug: ${w.slug}, ID: ${w.id}`);
    });
}

main()
    .catch(e => console.error(e))
    .finally(async () => {
        await prisma.$disconnect();
    });
