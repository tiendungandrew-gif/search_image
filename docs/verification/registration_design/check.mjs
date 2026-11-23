import { chromium, firefox } from '../../../frontend/node_modules/@playwright/test/index.mjs';
import AxeBuilder from '../../../frontend/node_modules/@axe-core/playwright/dist/index.mjs';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const results=[];
for(const [name,engine,width,height] of [['desktop',chromium,1440,1000],['mobile',chromium,390,844],['narrow',chromium,320,780],['firefox',firefox,1280,900]]) {
 const browser=await engine.launch();
 try {
 const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce'});
 if(name==='firefox')await context.addInitScript(()=>localStorage.setItem('lens.theme','dark'));
 const page=await context.newPage();
 await page.goto('http://localhost:5173');
 await page.getByRole('button',{name:'Đăng ký',exact:true}).click();
 await page.getByRole('heading',{name:'Tạo tài khoản Lens'}).waitFor();
 await page.waitForFunction(()=>document.activeElement?.id==='login-heading');
 const fields=await page.locator('.signup-identity-grid input').evaluateAll(inputs=>inputs.map(input=>({left:input.getBoundingClientRect().left,top:input.getBoundingClientRect().top})));
 if(width>600)assert.equal(fields[0].top,fields[1].top);
 else assert.ok(fields[1].top>fields[0].top);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.deepEqual((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()).violations,[]);
 await page.screenshot({path:`docs/verification/registration_design/${name}.png`,fullPage:true});
 let submitted=0;
 page.on('request',r=>{if(new URL(r.url()).pathname==='/api/v1/auth/register')submitted++;});
 await page.locator('#register-name').fill('Người dùng');
 await page.locator('#register-username').fill('demo_design');
 await page.locator('#register-password').fill('Design-check-only-2026!');
 await page.locator('#register-confirm').fill('Different-long-password');
 await page.getByRole('button',{name:'Tạo tài khoản',exact:true}).click();
 await page.getByRole('alert').filter({hasText:'chưa khớp'}).waitFor();
 assert.equal(submitted,0);
 await page.locator('#register-confirm').fill('Design-check-only-2026!');
 assert.equal(await page.getByRole('alert').count(),0);
 assert.equal(await page.locator('.signup-checks .is-valid').count(),2);
 await page.getByRole('button',{name:'Hiện mật khẩu'}).click();
 assert.equal(await page.locator('#register-confirm').getAttribute('type'),'text');
 await page.getByRole('button',{name:'Đăng nhập',exact:true}).click();
 await page.getByRole('heading',{name:'Đăng nhập vào Lens'}).waitFor();
 results.push({name,groupedFields:true,responsive:true,axeViolations:0,confirmationFeedback:true,cancel:true,registrationRequests:submitted});
 console.log(name,'PASS');
 }finally{await browser.close();}
}
fs.writeFileSync('docs/verification/registration_design/browser.json',JSON.stringify(results,null,2)+'\n');
