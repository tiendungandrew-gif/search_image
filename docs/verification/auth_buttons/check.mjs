import { chromium, firefox } from '../../../frontend/node_modules/@playwright/test/index.mjs';
import AxeBuilder from '../../../frontend/node_modules/@axe-core/playwright/dist/index.mjs';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const results=[];
for(const [name,engine,width,height] of [['desktop',chromium,1440,1000],['mobile',chromium,390,844],['narrow',chromium,320,780],['firefox',firefox,1280,1000]]){
 const browser=await engine.launch();
 try{
 const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce'});
 if(name==='firefox')await context.addInitScript(()=>localStorage.setItem('lens.theme','dark'));
 const page=await context.newPage();
 await page.goto('http://localhost:5173');
 const login=page.getByRole('button',{name:'Đăng nhập',exact:true});
 await login.waitFor();
 assert.equal(await login.isDisabled(),true);
 await page.locator('#login-username').fill('preview_only');
 await page.locator('#login-password').fill('Preview-only-password');
 assert.equal(await login.isEnabled(),true);
 await page.getByRole('heading',{name:'Đăng nhập vào Lens'}).click();
 const signup=page.getByRole('button',{name:'Đăng ký',exact:true});
 assert.ok((await signup.boundingBox()).height>=44);
 assert.ok((await login.boundingBox()).height>=44);
 assert.equal(await signup.evaluate(el=>getComputedStyle(el).textDecorationLine),'none');
 assert.deepEqual((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()).violations,[]);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.screenshot({path:`docs/verification/auth_buttons/login-${name}.png`,fullPage:true});
 await signup.click();
 await page.getByRole('heading',{name:'Tạo tài khoản Lens'}).waitFor();
 const back=page.getByRole('button',{name:'Đăng nhập',exact:true});
 assert.ok((await back.boundingBox()).height>=44);
 await page.screenshot({path:`docs/verification/auth_buttons/signup-${name}.png`,fullPage:true});
 await back.click();
 await page.getByRole('heading',{name:'Đăng nhập vào Lens'}).waitFor();
 results.push({name,primaryEnabledDisabled:true,secondaryButton:true,navigation:true,axeViolations:0,layout:true});
 console.log(name,'PASS');
 }finally{await browser.close();}
}
fs.writeFileSync('docs/verification/auth_buttons/browser.json',JSON.stringify(results,null,2)+'\n');
