/* Small, deliberately restricted Markdown renderer. Raw HTML is always escaped. */
function releaseNotesHTML(markdown) {
    const escape = text => text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
    const inline = text => escape(text).split(/(`[^`]+`)/g).map(part => {
        if(part.startsWith('`') && part.endsWith('`')) return '<code>'+part.slice(1,-1)+'</code>';
        return part.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
    }).join('');
    const output=[]; let list=null, paragraph=[];
    function flushParagraph() { if(paragraph.length) {output.push('<p>'+paragraph.join('<br>')+'</p>');paragraph=[];} }
    function closeList() { if(list) {output.push('</'+list+'>');list=null;} }
    for(const line of String(markdown || '').replace(/\r\n?/g,'\n').split('\n')) {
        const heading=line.match(/^ {0,3}(#{1,6})\s+(.+?)(?:\s+#+)?\s*$/);
        const item=line.match(/^\s*(?:[-+*]|(\d+)[.)])\s+(.+)$/);
        if(heading) {flushParagraph();closeList(); const level=Math.min(heading[1].length+1,6);output.push('<h'+level+'>'+inline(heading[2])+'</h'+level+'>');}
        else if(item) {flushParagraph();const type=item[1] ? 'ol' : 'ul';if(list!==type){closeList();list=type;output.push('<'+type+'>');}output.push('<li>'+inline(item[2])+'</li>');}
        else if(!line.trim()) {flushParagraph();closeList();}
        else {closeList();paragraph.push(inline(line));}
    }
    flushParagraph();closeList();return output.join('');
}
function renderReleaseNotes(element, markdown) {
    element.innerHTML=releaseNotesHTML(markdown || 'No release notes provided.');
}
