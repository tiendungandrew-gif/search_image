import { chromium, firefox } from '../../../frontend/node_modules/@playwright/test/index.mjs';
import AxeBuilder from '../../../frontend/node_modules/@axe-core/playwright/dist/index.mjs';
import { randomUUID } from 'node:crypto';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const results=[];
const password='QA-signup-only-password-2026!';
const users=[];
try {
for (const [name, engine, width, height] of [['desktop',chromium,1440,1000],['mobile',chromium,390,844],['narrow',chromium,320,780],['firefox',firefox,1280,900]]) {
 const username='qa_signup_'+randomUUID().replaceAll('-','').slice(0,16);
 users.push(username);
 const browser=await engine.launch();
 try {
 const context=await browser.newContext({baseURL:'http://127.0.0.1:5175',viewport:{width,height},reducedMotion:'reduce'});
 if(name==='firefox') await context.addInitScript(()=>localStorage.setItem('lens.theme','dark'));
 const page=await context.newPage();
 await page.goto('http://127.0.0.1:5175');
 await page.getByRole('button',{name:'Đăng ký',exact:true}).click();
 await page.getByRole('heading',{name:'Tạo tài khoản Lens'}).waitFor();
 await page.locator('#register-name').fill('Người dùng QA');
 await page.locator('#register-username').fill(username);
 await page.locator('#register-password').fill(password);
 await page.locator('#register-confirm').fill('a-different-password');
 let sent=0;
 page.on('request',r=>{if(new URL(r.url()).pathname==='/api/v1/auth/register')sent++;});
 await page.getByRole('button',{name:'Tạo tài khoản',exact:true}).click();
 await page.getByRole('alert').filter({hasText:'chưa khớp'}).waitFor();
 assert.equal(sent,0);
 await page.locator('#register-confirm').fill(password);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.deepEqual((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()).violations,[]);
 await page.screenshot({path:`docs/verification/registration/signup-${name}.png`,fullPage:true});
 const [registered]=await Promise.all([
  page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/auth/register'),
  page.getByRole('button',{name:'Tạo tài khoản',exact:true}).click(),
 ]);
 assert.equal(registered.status(),201,await registered.text());
 await page.getByRole('status').filter({hasText:'Tạo tài khoản thành công'}).waitFor();
 assert.equal(await page.locator('#login-username').inputValue(),username);
 assert.equal(await page.locator('#login-password').inputValue(),'');
 await page.getByRole('button',{name:'Đăng ký',exact:true}).click();
 await page.locator('#register-name').fill('QA Duplicate');
 await page.locator('#register-username').fill(username);
 await page.locator('#register-password').fill(password);
 await page.locator('#register-confirm').fill(password);
 const [duplicate]=await Promise.all([
  page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/auth/register'),
  page.getByRole('button',{name:'Tạo tài khoản',exact:true}).click(),
 ]);
 assert.equal(duplicate.status(),409);
 await page.getByRole('alert').filter({hasText:'không khả dụng'}).waitFor();
 await page.getByRole('button',{name:'Đăng nhập',exact:true}).click();
 await page.locator('#login-password').fill(password);
 const [login]=await Promise.all([
  page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/auth/login'),
  page.getByRole('button',{name:'Đăng nhập',exact:true}).click(),
 ]);
 assert.equal(login.status(),200);
 const account=(await login.json()).user;
 assert.equal(account.role,'user');
 assert.deepEqual(account.datasets,[]);
 assert.equal(account.is_demo,false);
 assert.equal((await page.request.get('/api/v1/admin/users')).status(),403);
 await page.getByRole('button',{name:'Đăng xuất',exact:true}).waitFor();
 await page.screenshot({path:`docs/verification/registration/empty-libraries-${name}.png`,fullPage:true});
 await page.getByRole('button',{name:'Đăng xuất',exact:true}).click();
 await page.getByRole('heading',{name:'Đăng nhập vào Lens'}).waitFor();
 results.push({name,signup:201,duplicate:409,passwordConfirmation:true,login:200,role:'user',datasets:0,adminDenied:403,logout:true,axeViolations:0});
 console.log(name,'PASS');
 } finally {await browser.close();}
}
} finally {
 fs.writeFileSync('docs/verification/registration/browser.json',JSON.stringify({results,qaUsers:users},null,2)+'\n');
}
