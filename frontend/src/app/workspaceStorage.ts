export type WorkspaceSnapshot<T> = {
  version: 1;
  updatedAt: string;
  value: T;
};

const DATABASE_NAME = "journal-study-workspace";
const STORE_NAME = "snapshots";

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, 1);
    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE_NAME);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function readWorkspace<T>(key: string): Promise<T | null> {
  if (typeof indexedDB === "undefined") {
    return null;
  }

  const database = await openDatabase();
  return new Promise((resolve, reject) => {
    const request = database
      .transaction(STORE_NAME, "readonly")
      .objectStore(STORE_NAME)
      .get(key);
    request.onsuccess = () => {
      const snapshot = request.result as WorkspaceSnapshot<T> | undefined;
      resolve(snapshot?.version === 1 ? snapshot.value : null);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function writeWorkspace<T>(key: string, value: T): Promise<void> {
  if (typeof indexedDB === "undefined") {
    return;
  }

  const database = await openDatabase();
  await new Promise<void>((resolve, reject) => {
    const request = database
      .transaction(STORE_NAME, "readwrite")
      .objectStore(STORE_NAME)
      .put({ version: 1, updatedAt: new Date().toISOString(), value }, key);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}
