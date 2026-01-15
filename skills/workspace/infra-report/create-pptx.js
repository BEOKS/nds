const pptxgen = require('pptxgenjs');
const path = require('path');

// html2pptx 모듈 경로
const html2pptx = require('/Users/leejs/.claude/skills/pptx/scripts/html2pptx');

async function createPresentation() {
    const pptx = new pptxgen();
    pptx.layout = 'LAYOUT_16x9';
    pptx.author = '인프라개발유닛';
    pptx.title = '인프라개발유닛 - 작업 명세서 (2025-08-04 ~ 2025-08-07)';
    pptx.subject = '주간 업무 보고';

    const workDir = '/Users/leejs/Project/nds/skills/workspace/infra-report';

    // 슬라이드 1: 타이틀
    console.log('Processing slide 1: Title...');
    await html2pptx(path.join(workDir, 'slide1-title.html'), pptx);

    // 슬라이드 2: Owen (방규빈)
    console.log('Processing slide 2: Owen...');
    await html2pptx(path.join(workDir, 'slide2-owen.html'), pptx);

    // 슬라이드 3: Chase (전창근)
    console.log('Processing slide 3: Chase...');
    await html2pptx(path.join(workDir, 'slide3-chase.html'), pptx);

    // 슬라이드 4: Zayden (이재성)
    console.log('Processing slide 4: Zayden...');
    await html2pptx(path.join(workDir, 'slide4-zayden.html'), pptx);

    // 슬라이드 5: Alan (김환승)
    console.log('Processing slide 5: Alan...');
    await html2pptx(path.join(workDir, 'slide5-alan.html'), pptx);

    // 슬라이드 6: 이슈사항
    console.log('Processing slide 6: Issues...');
    await html2pptx(path.join(workDir, 'slide6-issues.html'), pptx);

    // 저장
    const outputPath = path.join(workDir, 'infra-report-2025-08-04.pptx');
    await pptx.writeFile({ fileName: outputPath });
    console.log(`Presentation created: ${outputPath}`);
}

createPresentation().catch(console.error);
