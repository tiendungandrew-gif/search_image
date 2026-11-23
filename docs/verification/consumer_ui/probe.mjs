import {chromium} from '../../../frontend/node_modules/@playwright/test/index.mjs';
const browser=await chromium.launch();
try{
 const context=await browser.newContext({baseURL:'http://localhost:5173',viewport:{width:320,height:780},reducedMotion:'reduce'});
 await context.request.post('/api/v1/auth/quick-login',{data:{role:'user'},headers:{Origin:'http://localhost:5173'}});
 const page=await context.newPage();await page.goto('/');
 await page.locator('.result-card').nth(11).waitFor({timeout:25000});
 const rects=()=>page.locator('.result-card').evaluateAll(cards=>cards.map((card,i)=>{const media=card.querySelector('.result-media');const box=media.getBoundingClientRect();return {i,card:card.getBoundingClientRect().height,media:[box.width,box.height,box.top,box.left],imgHidden:card.querySelector('img')?.hidden,aspect:getComputedStyle(card.querySelector('.card-image-wrap')).aspectRatio};}));
 console.log('before',JSON.stringify(await rects()));
 await page.locator('.result-card').nth(2).scrollIntoViewIfNeeded();await page.waitForTimeout(1200);
 console.log('after',JSON.stringify(await rects()));
}finally{await browser.close();}
