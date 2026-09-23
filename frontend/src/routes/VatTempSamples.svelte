<script>
  import { onMount } from 'svelte';
  import { api, VAT_STATUS, toLocalInput, fromLocalInput } from '../lib/api.js';

  let vats = [];
  let lots = [];
  let rows = [];
  let error = '';
  let form = {
    vatId: '',
    seq: 1,
    tempC: 60,
    sampledAt: toLocalInput(new Date().toISOString()),
    recorderName: '染程操作员',
  };
  let editing = null;

  async function load() {
    error = '';
    try {
      [vats, lots, rows] = await Promise.all([
        api('/vats'),
        api('/dye-lots'),
        api('/vat-temp-samples'),
      ]);
      if (!form.vatId && vats.length) {
        const dyeing = vats.find((v) => v.status === 'dyeing');
        form.vatId = String((dyeing || vats[0]).id);
      }
      if (!editing) form.seq = nextSeqFor(form.vatId, rows);
    } catch (e) {
      error = e.message;
    }
  }

  onMount(load);

  function vatLabel(id) {
    const v = vats.find((x) => x.id === id);
    if (!v) return id;
    return `${v.vatCode}（${VAT_STATUS[v.status] || v.status}）`;
  }

  // 该缸下一个序号（新建时默认带出，可手改）
  function nextSeqFor(vatId, sampleRows) {
    const seqs = sampleRows
      .filter((r) => String(r.vatId) === String(vatId))
      .map((r) => r.seq);
    return seqs.length ? Math.max(...seqs) + 1 : 1;
  }

  function onVatChange() {
    if (!editing) form.seq = nextSeqFor(form.vatId, rows);
  }

  $: vatSamples = rows
    .filter((r) => String(r.vatId) === String(form.vatId))
    .sort((a, b) => a.seq - b.seq);

  // 与后端一致的收染链判定摘要（仅展示，最终以后端判定为准）
  $: chain = chainInfo(vatSamples, lots, form.vatId);

  function chainInfo(samples, allLots, vatId) {
    let best = [];
    let cur = [];
    for (const s of samples) {
      if (cur.length && s.seq !== cur[cur.length - 1].seq + 1) cur = [];
      cur.push(s);
      if (cur.length > best.length) best = [...cur];
    }
    let maxDelta = 0;
    for (let i = 1; i < best.length; i++) {
      maxDelta = Math.max(maxDelta, Math.abs(best[i].tempC - best[i - 1].tempC));
    }
    const latestAt = samples.length
      ? Math.max(...samples.map((s) => new Date(s.sampledAt).getTime()))
      : null;
    const vatLots = allLots.filter((l) => String(l.vatId) === String(vatId));
    const latestLot = vatLots.length
      ? Math.max(...vatLots.map((l) => new Date(l.startedAt).getTime()))
      : null;
    const countOk = best.length >= 3;
    const deltaOk = maxDelta <= 8;
    const timeOk = !latestLot || (latestAt !== null && latestAt > latestLot);
    return {
      runLen: best.length,
      maxDelta,
      countOk,
      deltaOk,
      timeOk,
      ready: countOk && deltaOk && timeOk,
    };
  }

  async function save() {
    error = '';
    try {
      const body = {
        vatId: Number(form.vatId),
        seq: Number(form.seq),
        tempC: Number(form.tempC),
        sampledAt: fromLocalInput(form.sampledAt),
        recorderName: form.recorderName.trim(),
      };
      if (editing) {
        await api(`/vat-temp-samples/${editing}`, { method: 'PUT', body: JSON.stringify(body) });
      } else {
        await api('/vat-temp-samples', { method: 'POST', body: JSON.stringify(body) });
      }
      editing = null;
      form = { ...form, sampledAt: toLocalInput(new Date().toISOString()) };
      await load();
    } catch (e) {
      error = e.message;
    }
  }

  function startEdit(row) {
    editing = row.id;
    form = {
      vatId: String(row.vatId),
      seq: row.seq,
      tempC: row.tempC,
      sampledAt: toLocalInput(row.sampledAt),
      recorderName: row.recorderName,
    };
  }

  function cancelEdit() {
    editing = null;
    form.seq = nextSeqFor(form.vatId, rows);
  }

  async function remove(id) {
    if (!confirm('确认删除该采样点？')) return;
    error = '';
    try {
      await api(`/vat-temp-samples/${id}`, { method: 'DELETE' });
      await load();
    } catch (e) {
      error = e.message;
    }
  }
</script>

<h1 class="page-title">缸温采样链</h1>
<p class="page-sub">
  仅染色中染缸可登记；同缸序号从 1 起且唯一。收染需：≥3 个连续序号、链内相邻缸温差 ≤8℃、最新采样晚于该缸最新染程开始。
</p>

<div class="panel" style="margin-bottom:1rem;">
  <div class="form-grid">
    <label
      >染缸
      <select bind:value={form.vatId} on:change={onVatChange}>
        {#each vats as v}
          <option value={String(v.id)}
            >{v.vatCode} · {VAT_STATUS[v.status] || v.status} · {v.fiberType}</option
          >
        {/each}
      </select>
    </label>
    <label>序号 <input type="number" min="1" step="1" bind:value={form.seq} /></label>
    <label>缸温 ℃ <input type="number" step="0.1" bind:value={form.tempC} /></label>
    <label>采样时刻 <input type="datetime-local" bind:value={form.sampledAt} /></label>
    <label>记录人 <input bind:value={form.recorderName} /></label>
  </div>
  <div class="toolbar">
    <button class="btn" type="button" on:click={save}>{editing ? '保存修改' : '登记采样'}</button>
    {#if editing}
      <button class="btn ghost" type="button" on:click={cancelEdit}>取消</button>
    {/if}
  </div>
  {#if error}<p class="err">{error}</p>{/if}
</div>

{#if form.vatId}
  <div class="panel" style="margin-bottom:1rem;">
    <p class="chain-line">
      当前缸 {vatLabel(Number(form.vatId))}：最长连续序号链
      <strong>{chain.runLen}</strong> 点（需 ≥3 {chain.countOk ? '✓' : '✗'}） · 链内最大相邻温差
      <strong>{chain.maxDelta.toFixed(1)}℃</strong>（≤8℃ {chain.deltaOk ? '✓' : '✗'}） · 最新采样时刻{chain.timeOk
        ? '已晚于'
        : '未晚于'}最新染程开始（{chain.timeOk ? '✓' : '✗'}）
      →
      {#if chain.ready}
        <span class="ok-msg">链已闭合，可收染</span>
      {:else}
        <span class="err" style="display:inline;margin:0;">链未闭合，暂不可收染</span>
      {/if}
    </p>
  </div>
{/if}

<div class="panel">
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>染缸</th>
        <th>序号</th>
        <th>缸温</th>
        <th>采样时刻</th>
        <th>记录人</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {#each rows as row}
        <tr>
          <td>{row.id}</td>
          <td>{vatLabel(row.vatId)}</td>
          <td>{row.seq}</td>
          <td>{row.tempC}℃</td>
          <td>{new Date(row.sampledAt).toLocaleString()}</td>
          <td>{row.recorderName}</td>
          <td class="row-actions">
            <button class="btn ghost small" type="button" on:click={() => startEdit(row)}>编辑</button>
            <button class="btn danger small" type="button" on:click={() => remove(row.id)}>删除</button>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .chain-line {
    margin: 0;
    font-size: 0.88rem;
    color: var(--indigo-mist);
  }

  .chain-line strong {
    color: var(--foam);
  }
</style>
