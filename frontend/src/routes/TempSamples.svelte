<script>
  import { onMount } from 'svelte';
  import { api, VAT_STATUS, toLocalInput, fromLocalInput } from '../lib/api.js';

  let vats = [];
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
      [vats, rows] = await Promise.all([api('/vats'), api('/temp-samples')]);
      const dyeing = vats.filter((v) => v.status === 'dyeing');
      if (!editing) {
        if (!form.vatId && dyeing.length) form.vatId = String(dyeing[0].id);
        if (form.vatId) form.seq = nextSeq(Number(form.vatId));
      }
    } catch (e) {
      error = e.message;
    }
  }

  onMount(load);

  function vatLabel(id) {
    const v = vats.find((x) => x.id === id);
    return v ? `${v.vatCode}（${VAT_STATUS[v.status] || v.status}）` : id;
  }

  function nextSeq(vatId) {
    const seqs = rows.filter((r) => r.vatId === vatId).map((r) => r.seq);
    return seqs.length ? Math.max(...seqs) + 1 : 1;
  }

  function onVatChange() {
    form.seq = nextSeq(Number(form.vatId));
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
        await api(`/temp-samples/${editing}`, { method: 'PUT', body: JSON.stringify(body) });
      } else {
        await api('/temp-samples', { method: 'POST', body: JSON.stringify(body) });
      }
      editing = null;
      form = {
        ...form,
        seq: form.vatId ? nextSeq(Number(form.vatId)) : 1,
        tempC: 60,
        sampledAt: toLocalInput(new Date().toISOString()),
      };
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

  async function remove(id) {
    if (!confirm('确认删除该采样点？断号会导致缸温链不完整。')) return;
    error = '';
    try {
      await api(`/temp-samples/${id}`, { method: 'DELETE' });
      await load();
    } catch (e) {
      error = e.message;
    }
  }
</script>

<h1 class="page-title">缸温链</h1>
<p class="page-sub">
  采样挂染缸，仅染程中缸可登记；同缸序号自 1 起唯一。连续 ≥3 点、相邻温差 ≤8℃、末点晚于最新染程开始方可收染。
</p>

<div class="panel" style="margin-bottom:1rem;">
  <div class="form-grid">
    <label
      >所属染缸
      <select bind:value={form.vatId} on:change={onVatChange}>
        {#each vats as v}
          <option value={String(v.id)}
            >{v.vatCode} · {VAT_STATUS[v.status] || v.status} · 已有 {v.sampleCount ?? 0} 点</option
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
      <button
        class="btn ghost"
        type="button"
        on:click={() => {
          editing = null;
          load();
        }}>取消</button
      >
    {/if}
  </div>
  {#if error}<p class="err">{error}</p>{/if}
</div>

<div class="panel">
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>所属染缸</th>
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
