import jsPDF from 'jspdf';
import html2canvas from 'html2canvas-pro';
import { toast } from 'svelte-sonner';

export const downloadPdf = async (note) => {
// Check if we are currently viewing this note
// The URL structure is /notes/[id]
const currentPath = window.location.pathname;
const isCurrentNote = currentPath === `/notes/${note.id}`;

if (isCurrentNote) {
try {
window.print();
} catch (error) {
console.error('Error printing note', error);
toast.error(`${error}`);
}
} else {
try {
// Define a fixed virtual screen size
const virtualWidth = 1024; // Fixed width (adjust as needed)
const virtualHeight = 1400; // Fixed height (adjust as needed)

// STEP 1. Get a DOM node to render
const html = note.data?.content?.html ?? '';
let node;
if (html instanceof HTMLElement) {
node = html;
} else {
// If it's HTML string, render to a temporary hidden element
node = document.createElement('div');
// Apply editor classes for better styling
node.className =
'prose dark:prose-invert max-w-none px-4 py-4 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100';

node.style.width = `${virtualWidth}px`;
// node.style.padding = '20px';
// node.style.backgroundColor = 'white';
// node.style.color = 'black';

// Add title
node.innerHTML = `<h1 class="text-2xl font-medium mb-4">${note.title}</h1>` + html;
document.body.appendChild(node);
}

// Render to canvas with predefined width
const canvas = await html2canvas(node, {
useCORS: true,
scale: 2, // Keep at 1x to avoid unexpected enlargements
width: virtualWidth, // Set fixed virtual screen width
windowWidth: virtualWidth, // Ensure consistent rendering
windowHeight: virtualHeight
});

// Remove hidden node if needed
if (!(html instanceof HTMLElement)) {
document.body.removeChild(node);
}

const imgData = canvas.toDataURL('image/png');

// A4 page settings
const pdf = new jsPDF('p', 'mm', 'a4');
const imgWidth = 210; // A4 width in mm
const pageHeight = 297; // A4 height in mm

// Maintain aspect ratio
const imgHeight = (canvas.height * imgWidth) / canvas.width;
let heightLeft = imgHeight;
let position = 0;

pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
heightLeft -= pageHeight;

// Handle additional pages
while (heightLeft > 0) {
position -= pageHeight;
pdf.addPage();

pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
heightLeft -= pageHeight;
}

pdf.save(`${note.title}.pdf`);
} catch (error) {
console.error('Error generating PDF', error);
toast.error(`${error}`);
}
}
};
