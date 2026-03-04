
# 방화벽 정책 요청

<!-- 가비아(83) 의 IN / OUT 정책을 관리 합니다. -->

## 요청 사항 기록 <!-- ( 작성 : 요청자 ) -->
|구분|내용|
|---|---|
|요청자|<!-- 요청자 이름 기록 -->|
|작업 대상|<!-- 서버, 도메인, k8s 등 대상 기록 -->|
|비고|<!-- src 또는 dest 의 역할 기록 (개발/IDC운영/테스트/등등..) -->|

### 정책 요청서

<!-- 작업에 대해 설명합니다. -->

|Source|Destination|Port|Period|
|---|---|---|---|
|<!-- 출발지 IP 또는 대상자 -->|<!-- 목적지 IP 또는 대상자-->|<!-- 정책 적용 포트 -->|<!-- 정책 적용 기간 -->|

- [ ] ✅ 허용 
- [ ] ❌ 차단 


### 가비아(83) 운영 해외 IP [Confluence](https://confluence.gabia.com/pages/resumedraft.action?draftId=186869568&draftShareId=9f44aa45-57a3-46ce-8c7a-7b8378949ff1&)

<details>
  <summary> 📌 가비아(83) 운영 해외 IP 펼치기 </summary>
  <br>
  <table>
    <thead>
      <tr>
        <th>AWS Name</th>
        <th>IP</th>
        <th>Azure Name</th>
        <th>IP</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>Gabia-aws-bastion</td><td>13.124.130.232</td><td>Gabia-azure-bastion</td><td>20.214.234.137</td></tr>
      <tr><td>gabia-dns-asg-1</td><td>3.39.119.77</td><td>gabia-dns-azure-asg-1</td><td>4.230.16.96</td></tr>
      <tr><td>gabia-dns-asg-2</td><td>3.39.163.211</td><td>gabia-dns-azure-asg-2</td><td>20.41.116.70</td></tr>
      <tr><td>gabia-dns-asg-3</td><td>52.79.81.154</td><td>gabia-dns-azure-asg-3</td><td>52.141.29.161</td></tr>
      <tr><td>gabia-dns-asg-4</td><td>52.79.93.192</td><td>Gabia-azure-dns-maneger</td><td>20.249.103.48</td></tr>
      <tr><td>gabia-dns-asg-5</td><td>3.37.111.53</td><td>nginx-proxy-azure-1</td><td>48.216.193.24</td></tr>
      <tr><td>gabia-dns-asg-6</td><td>3.37.77.59</td><td>nginx-proxy-azure-2</td><td>48.216.198.215</td></tr>
      <tr><td>Gabia-DNS(Manage)</td><td>43.201.164.92</td><td>nginx-proxy-azure-3</td><td>4.157.64.99</td></tr>
      <tr><td>www-haproxy-1</td><td>34.237.48.96</td><td>nginx-proxy-azure-4</td><td>4.157.64.114</td></tr>
      <tr><td>www-haproxy-2</td><td>54.147.122.101</td><td>gabia-azure-ims</td><td>20.39.199.200</td></tr>
      <tr><td>www-nginx-1</td><td>44.209.56.114</td></tr>
      <tr><td>www-nginx-2</td><td>44.213.7.173</td></tr>
      <tr><td>dns-cache-1</td><td>3.39.166.212</td></tr>
      <tr><td>dns-cache-2</td><td>3.39.55.44</td></tr>
      <tr><td>gabia-aws-ims</td><td>15.164.190.29</td></tr>
      <tr><td>global-rdap1</td><td>43.200.238.80</td></tr>
      <tr><td>global-rdap2</td><td>43.202.206.88</td></tr>
    </tbody>
  </table>
</details>


### 요청자 확인 <!-- 요청자 체크 박스 확인 -->

<!-- 
* 요청자 가비아 IP 확인
-->

- [ ] 가비아(83) 운영 해외 IP 존재 여부 확인
- [ ] 영향 범위 및 검증 확인

## 요청 승인 시 사항 점검 <!-- ( 작성 : 요청 유닛/팀장 ) -->

- [ ] 가비아(83) 운영 해외 IP 존재 여부 확인
- [ ] 영향 범위 및 검증 확인

### 지시 사항 <!-- ( 작성 : 요청 유닛/팀장 ) -->

<!-- 자유롭게 기술합니다. -->

##

### 작업자 확인 <!-- 작업자 체크 박스 확인 -->

- 방화벽 룰 존재 여부 확인 (화이트 IP)
    - [ ] 공인/사설 물리 방화벽
    - [ ] 클라우드 콘솔 방화벽
- 생성 환경 체크
    - [ ] intercloud
    - [ ] gCloud Gen1 / Gen2
    - [ ] Physical
- 생성 존 체크
    - [ ] DMZ
    - [ ] OP (QA)
    - [ ] STAGE
    - [ ] DEV

- 정책 요청서 기록 (요청자, 요청승인자 추가)
    - [ ] 전자 결재 (Gitlab 정책 요청서 주소 또는 요청 번호 기록)

### 승인자 확인 <!-- 승인자 체크 박스 확인 -->

- [ ] 작업 시간 확인
- [ ] 영향 범위 확인
- [ ] 작업 계획 검토
- [ ] 최종 사용 환경 승인

### 특이 사항 기록 <!-- ( 작성 : 운영팀 ) -->

<!-- 자유롭게 기술합니다. -->














