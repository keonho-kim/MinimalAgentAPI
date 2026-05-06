export const queryKeys = {
  files(userId: string, sessionUuid: string) {
    return ["files", userId, sessionUuid] as const;
  },
  filePreview(userId: string, sessionUuid: string, path: string) {
    return ["file-preview", userId, sessionUuid, path] as const;
  },
  fileSearch(userId: string, sessionUuid: string, query: string, limit: number) {
    return ["file-search", userId, sessionUuid, query, limit] as const;
  },
  skillSearch(userId: string, sessionUuid: string, query: string, limit: number) {
    return ["skill-search", userId, sessionUuid, query, limit] as const;
  },
};
