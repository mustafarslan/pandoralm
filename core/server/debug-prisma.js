
const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
    const slug = 'test1-57575330';
    const workspace = await prisma.workspaces.findFirst({
        where: { slug: slug },
        include: { documents: true }
    });

    if (!workspace) {
        console.log(`Workspace with slug ${slug} not found.`);
        return;
    }

    console.log(`Workspace: ${workspace.name} (ID: ${workspace.id})`);
    console.log(`Documents count: ${workspace.documents.length}`);

    const vectorCount = await prisma.document_vectors.count({
        where: { docId: { in: workspace.documents.map(d => d.docId) } }
    });

    console.log(`Document Vectors count in SQL: ${vectorCount}`);
}

main()
    .catch(e => console.error(e))
    .finally(async () => {
        await prisma.$disconnect();
    });
