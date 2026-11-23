import { chromium, firefox } from '../../../frontend/node_modules/@playwright/test/index.mjs';
import AxeBuilder from '../../../frontend/node_modules/@axe-core/playwright/dist/index.mjs';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import fs from 'node:fs';
const results=[];
for(const [name,engine,width,height] of [['desktop',chromium,1440,1000],['mobile',chromium,390,844],['narrow',chromium,320,780],['firefox',firefox,1280,900]]){
 const browser=await engine.launch();
 try{
 const opts={baseURL:'http://127.0.0.1:5175',viewport:{width,height},reducedMotion:'reduce'};
 const adminContext=await browser.newContext(opts), memberContext=await browser.newContext(opts);
 const admin=await adminContext.newPage(), member=await memberContext.newPage();
 await admin.goto('/');
 await admin.locator('#login-username').fill('qa_shared_admin');
 await admin.locator('#login-password').fill('QA-shared-admin-only-2026!');
 await admin.getByRole('button',{name:'Đăng nhập',exact:true}).click();
 await admin.getByRole('button',{name:'Đăng xuất',exact:true}).waitFor();
 const libraries=(await (await admin.request.get('/api/v1/admin/datasets')).json()).datasets;
 const common=libraries.find(d=>d.key==='qa_common_browser'), privateLibrary=libraries.find(d=>d.key==='qa_private_browser');
 assert.ok(common&&privateLibrary);
 const commonImage=(await (await admin.request.get(`/api/v1/admin/images?dataset_id=${common.id}`)).json()).images[0].id;
 const privateImage=(await (await admin.request.get(`/api/v1/admin/images?dataset_id=${privateLibrary.id}`)).json()).images[0].id;
 async function share(enabled){
  await admin.goto('/admin/datasets');
  const tile=admin.locator('.dataset-tile').filter({hasText:'QA Common Images'});
  await tile.locator('summary').click();
  await tile.getByRole('checkbox',{name:'Chia sẻ cho mọi thành viên'}).setChecked(enabled);
  const [response]=await Promise.all([
   admin.waitForResponse(r=>r.request().method()==='PATCH'&&new URL(r.url()).pathname===`/api/v1/admin/datasets/${common.id}`),
   tile.getByRole('button',{name:'Lưu thư viện',exact:true}).click(),
  ]);
  assert.equal(response.status(),200);
  await admin.waitForFunction(()=>!document.querySelector('.dataset-tile button[disabled]'));
 }
 await share(true);
 const tile=admin.locator('.dataset-tile').filter({hasText:'QA Common Images'});
 if(!await tile.getByRole('checkbox',{name:'Chia sẻ cho mọi thành viên'}).isVisible())await tile.locator('summary').click();
 assert.deepEqual((await new AxeBuilder({page:admin}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()).violations,[]);
 assert.equal(await admin.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await admin.screenshot({path:`docs/verification/shared_members/libraries-${name}.png`,fullPage:true});
 const username='qa_shared_'+randomUUID().replaceAll('-','').slice(0,12), displayName='QA Member '+name, password='QA-shared-user-only-2026!';
 await member.goto('/');
 await member.getByRole('button',{name:'Đăng ký',exact:true}).click();
 await member.locator('#register-name').fill(displayName);
 await member.locator('#register-username').fill(username);
 await member.locator('#register-password').fill(password);
 await member.locator('#register-confirm').fill(password);
 await member.getByRole('button',{name:'Tạo tài khoản',exact:true}).click();
 await member.getByRole('status').filter({hasText:'Tạo tài khoản thành công'}).waitFor();
 await member.locator('#login-password').fill(password);
 const [login]=await Promise.all([member.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/auth/login'),member.getByRole('button',{name:'Đăng nhập',exact:true}).click()]);
 assert.equal(login.status(),200);
 const account=(await login.json()).user;
 assert.equal(account.role,'user');assert.equal(account.is_active,true);
 assert.deepEqual(account.datasets.map(d=>d.id),[common.id]);
 assert.equal(account.datasets[0].shared_with_members,true);
 assert.equal((await member.request.get(`/api/v1/images/${commonImage}/content`)).status(),200);
 assert.equal((await member.request.get(`/api/v1/images/${privateImage}/content`)).status(),404);
 assert.equal((await member.request.get('/api/v1/admin/users')).status(),403);
 await member.getByRole('button',{name:'Đăng xuất',exact:true}).waitFor();
 await member.locator('.library-access summary').click();
 await member.locator('.library-list').getByText('QA Common Images',{exact:false}).waitFor();
 assert.equal(await member.locator('.library-list').getByText('QA Private Images',{exact:false}).count(),0);
 await member.screenshot({path:`docs/verification/shared_members/member-${name}.png`,fullPage:true});
 await share(false);
 assert.deepEqual((await(await member.request.get('/api/v1/auth/me')).json()).user.datasets,[]);
 assert.equal((await member.request.get(`/api/v1/images/${commonImage}/content`)).status(),404);
 await share(true);
 assert.equal((await member.request.get(`/api/v1/images/${commonImage}/content`)).status(),200);
 await admin.goto('/admin/users');
 const userTile=admin.locator('.user-editor').filter({hasText:displayName});
 await userTile.locator('summary').click();
 const automatic=userTile.getByRole('checkbox',{name:/QA Common Images/});
 assert.equal(await automatic.isChecked(),true);assert.equal(await automatic.isDisabled(),true);
 await admin.screenshot({path:`docs/verification/shared_members/accounts-${name}.png`,fullPage:true});
 const [revoked]=await Promise.all([admin.waitForResponse(r=>new URL(r.url()).pathname===`/api/v1/admin/users/${account.id}/sessions/revoke`),userTile.getByRole('button',{name:'Đăng xuất mọi thiết bị',exact:true}).click()]);
 assert.equal(revoked.status(),200);
 assert.equal((await(await member.request.get('/api/v1/auth/me')).json()).user,null);
 await member.reload();
 await member.getByRole('heading',{name:'Đăng nhập vào Lens'}).waitFor();
 results.push({name,signupImmediate:true,sharedRead:200,privateDenied:404,adminDenied:403,liveUnshare:true,automaticAccessDisplay:true,sessionRevoked:true,axeViolations:0});console.log(name,'PASS');
 }finally{await browser.close();}
}
fs.writeFileSync('docs/verification/shared_members/browser.json',JSON.stringify(results,null,2)+'\n');
