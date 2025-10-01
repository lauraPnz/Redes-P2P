# status_node.py
import os
import threading
from utilidades import sha256_file, now_ts, safe_join, read_json, write_json

class NodeState:
    def __init__(self, cfg):
        self.directory = os.path.abspath(cfg["directory"])
        self.host, port_str = cfg["self"].split(':')
        self.port = int(port_str)
        self.node_id = cfg["self"]
        self.peers = [p for p in cfg["peers"] if p != cfg["self"]]
        self.sync_interval = int(cfg.get("sync_interval_seconds", 5))
        os.makedirs(self.directory, exist_ok=True)

        self.meta_path = os.path.join(self.directory, ".p2pmeta.json")
        self.meta = read_json(self.meta_path, {"files": {}, "tombstones": {}})

        self.lock = threading.RLock()

    def scan_and_update_meta(self):
        with self.lock:
            current = {}
            for root, _, files in os.walk(self.directory):
                for fname in files:
                    if fname == ".p2pmeta.json":
                        continue
                    full = os.path.join(root, fname)
                    rel = os.path.relpath(full, self.directory)
                    try:
                        st = os.stat(full)
                    except FileNotFoundError:
                        continue
                    current[rel] = {
                        "mtime": int(st.st_mtime),
                        "sha256": sha256_file(full),
                    }

            prev_files = set(self.meta["files"].keys())
            curr_files = set(current.keys())
            removed = prev_files - curr_files
            for r in removed:
                ts_entry = self.meta["tombstones"].get(r, {})
                ts_entry["deleted_at"] = max(int(ts_entry.get("deleted_at", 0)), now_ts())
                ts_entry["by"] = self.node_id
                self.meta["tombstones"][r] = ts_entry
                self.meta["files"].pop(r, None)

            for rel, info in current.items():
                self.meta["files"][rel] = info
                if rel in self.meta["tombstones"]:
                    self.meta["tombstones"].pop(rel, None)

            write_json(self.meta_path, self.meta)

    def index_payload(self):
        with self.lock:
            return {
                "node_id": self.node_id,
                "generated_at": now_ts(),
                "files": self.meta["files"],
            }

    def tombstones_payload(self):
        with self.lock:
            return {
                "node_id": self.node_id,
                "generated_at": now_ts(),
                "tombstones": self.meta["tombstones"]
            }

    def apply_remote_tombstones(self, remote):
        changed = False
        with self.lock:
            for name, ts_info in remote.get("tombstones", {}).items():
                r_del = int(ts_info.get("deleted_at", 0))
                local_file = self.meta["files"].get(name)
                local_ts = int(self.meta["tombstones"].get(name, {}).get("deleted_at", 0))

                if r_del > local_ts:
                    self.meta["tombstones"][name] = {"deleted_at": r_del, "by": ts_info.get("by")}
                    if local_file:
                        lf_mtime = int(local_file.get("mtime", 0))
                        if r_del >= lf_mtime:
                            full = safe_join(self.directory, name)
                            if os.path.exists(full):
                                try:
                                    os.remove(full)
                                except Exception:
                                    pass
                            self.meta["files"].pop(name, None)
                            changed = True
            if changed:
                write_json(self.meta_path, self.meta)
        return changed

    def need_download(self, name, remote_mtime, remote_hash, remote_node):
        with self.lock:
            local = self.meta["files"].get(name)
            tomb = self.meta["tombstones"].get(name)
            if tomb and int(tomb.get("deleted_at", 0)) >= int(remote_mtime):
                return False
            if not local:
                return True
            l_mtime = int(local["mtime"])
            if int(remote_mtime) > l_mtime:
                return True
            if int(remote_mtime) < l_mtime:
                return False
            if local["sha256"] == remote_hash:
                return False
            return str(remote_node) > str(self.node_id)

    def save_downloaded_file(self, fname, data: bytes, mtime: int):
        """ Salva o arquivo e ajusta seu tempo de modificação. """
        full = safe_join(self.directory, fname)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        tmp_path = full + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(data)
        
        # **ALTERAÇÃO IMPORTANTE**: Ajusta o tempo de modificação do arquivo
        try:
            os.utime(tmp_path, (now_ts(), mtime))
        except Exception as e:
            print(f"Aviso: não foi possível definir o mtime para {fname}: {e}")
        
        os.replace(tmp_path, full)
        
        # NÃO é mais necessário chamar scan_and_update_meta() aqui.
        # O scan no início do próximo sync_loop cuidará de atualizar o meta.
        # Isso evita escritas excessivas no disco.